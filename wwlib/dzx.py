
from fs_helpers import *

class DZx: # DZR or DZS, same format
  def __init__(self, file_entry):
    self.file_entry = file_entry
    data = self.file_entry.data
    
    num_chunks = read_u32(data, 0)
    
    self.chunks = []
    for chunk_index in range(0, num_chunks):
      offset = 4 + chunk_index*0xC
      chunk = Chunk(self.file_entry)
      chunk.read(offset)
      self.chunks.append(chunk)
  
  def entries_by_type(self, chunk_type):
    entries = []
    for chunk in self.chunks:
      if chunk_type == chunk.chunk_type:
        entries += chunk.entries
    return entries
  
  def entries_by_type_and_layer(self, chunk_type, layer):
    entries = []
    for chunk in self.chunks:
      if chunk_type == chunk.chunk_type and layer == chunk.layer:
        entries += chunk.entries
    return entries
  
  def add_entity(self, chunk_type, layer=None):
    chunk_to_add_entity_to = None
    for chunk in self.chunks:
      if chunk_type == chunk.chunk_type and layer == chunk.layer:
        chunk_to_add_entity_to = chunk
        break
    
    if chunk_to_add_entity_to is None:
      chunk_to_add_entity_to = Chunk(self.file_entry)
      chunk_to_add_entity_to.chunk_type = chunk_type
      chunk_to_add_entity_to.layer = layer
      self.chunks.append(chunk_to_add_entity_to)
    
    entity = chunk_to_add_entity_to.entry_class(self.file_entry)
    chunk_to_add_entity_to.entries.append(entity)
    
    return entity
  
  def save_changes(self):
    data = self.file_entry.data
    data.truncate(0)
    
    offset = 0
    write_u32(data, offset, len(self.chunks))
    offset += 4
    
    for chunk in self.chunks:
      chunk.offset = offset
      write_str(data, chunk.offset, chunk.fourcc, 4)
      write_u32(data, chunk.offset+4, len(chunk.entries))
      write_u32(data, chunk.offset+8, 0) # Placeholder for first entry offset
      offset += 0xC
    
    for chunk in self.chunks:
      first_entry_offset = offset
      write_u32(data, chunk.offset+8, first_entry_offset)
      
      for entry in chunk.entries:
        if entry is None:
          raise Exception("Tried to save unknown chunk type: %s" % chunk.chunk_type)
        
        entry.offset = offset
        entry.save_changes()
        
        offset += chunk.entry_class.DATA_SIZE
    
    # Pad the length of this file to 0x20 bytes.
    file_size = offset
    padded_file_size = (file_size + 0x1F) & ~0x1F
    padding_size_needed = padded_file_size - file_size
    write_bytes(data, offset, b"\xFF"*padding_size_needed)

class Chunk:
  LAYER_CHAR_TO_LAYER_INDEX = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'a': 10, 'b': 11}
  
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
    
    self.entries = []
    self.layer = None
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.chunk_type = read_str(data, self.offset, 4)
    num_entries = read_u32(data, self.offset+4)
    first_entry_offset = read_u32(data, self.offset+8)
    
    # Some types of chunks are conditional and only appear on certain layers. The 4th character of their type determines what letter they appear on.
    if self.chunk_type.startswith("TRE") or self.chunk_type.startswith("ACT") or self.chunk_type.startswith("SCO"):
      layer_char = self.chunk_type[3]
      if layer_char in self.LAYER_CHAR_TO_LAYER_INDEX:
        self.layer = self.LAYER_CHAR_TO_LAYER_INDEX[layer_char]
    if self.chunk_type.startswith("TRE"):
      self.chunk_type = "TRES"
    if self.chunk_type.startswith("ACT"):
      self.chunk_type = "ACTR"
    if self.chunk_type.startswith("SCO"):
      self.chunk_type = "SCOB"
    
    if self.entry_class is None:
      #raise Exception("Unknown chunk type: " + self.chunk_type)
      self.entries = [None]*num_entries
      return
    
    #print("First entry offset: %X" % first_entry_offset)
    
    entry_size = self.entry_class.DATA_SIZE
    
    for entry_index in range(0, num_entries):
      entry_offset = first_entry_offset + entry_index*entry_size
      entry = self.entry_class(self.file_entry)
      entry.read(entry_offset)
      self.entries.append(entry)
  
  @property
  def entry_class(self):
    class_name = self.chunk_type
    if class_name[0].isdigit():
      class_name = "_" + class_name
    return globals().get(class_name, None)
  
  @property
  def fourcc(self):
    fourcc = self.chunk_type
    if self.layer:
      assert 0 <= self.layer <= 11
      fourcc = fourcc[:3]
      fourcc += "%x" % self.layer
    return fourcc

class TRES:
  DATA_SIZE = 0x20
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.name = read_str(data, offset, 8)
    
    self.params = read_u32(data, offset+8)
    
    self.x_pos = read_float(data, offset+0x0C)
    self.y_pos = read_float(data, offset+0x10)
    self.z_pos = read_float(data, offset+0x14)
    self.room_num = read_u16(data, offset+0x18)
    self.y_rot = read_u16(data, offset+0x1A)
    
    self.item_id = read_u8(data, offset+0x1C)
    self.flag_id = read_u8(data, offset+0x1D)
    
    self.padding = read_u16(data, offset + 0x1E)
    
  def save_changes(self):
    data = self.file_entry.data
    
    write_str(data, self.offset, self.name, 8)
    
    write_u32(data, self.offset+0x08, self.params)
    
    write_float(data, self.offset+0x0C, self.x_pos)
    write_float(data, self.offset+0x10, self.y_pos)
    write_float(data, self.offset+0x14, self.z_pos)
    write_u16(data, self.offset+0x18, self.room_num)
    write_u16(data, self.offset+0x1A, self.y_rot)
    
    write_u8(data, self.offset+0x1C, self.item_id)
    write_u8(data, self.offset+0x1D, self.flag_id)
    
    write_u16(data, self.offset+0x1E, self.padding)
  
  @property
  def chest_type(self):
    return ((self.params & 0x00F00000) >> 20)
  
  @chest_type.setter
  def chest_type(self, value):
    self.params = (self.params & (~0x00F00000)) | ((value&0xF) << 20)

  @property
  def appear_condition_switch(self):
    return ((self.params & 0x000FF000) >> 12)
  
  @appear_condition_switch.setter
  def appear_condition_switch(self, value):
    self.params = (self.params & (~0x000FF000)) | ((value&0xFF) << 12)

  @property
  def opened_flag(self):
    return ((self.params & 0x00000F80) >> 8)
  
  @opened_flag.setter
  def opened_flag(self, value):
    self.params = (self.params & (~0x00000F80)) | ((value&0x1F) << 7)

  @property
  def appear_condition_type(self):
    return ((self.params & 0x0000007F) >> 0)
  
  @appear_condition_type.setter
  def appear_condition_type(self, value):
    self.params = (self.params & (~0x0000007F)) | ((value&0x7F) << 0)

class SCOB:
  DATA_SIZE = 0x24
  
  SALVAGE_NAMES = [
    "Salvage",
    "SwSlvg",
    "Salvag2",
    "SalvagN",
    "SalvagE",
    "SalvFM",
  ]
  
  BURIED_PIG_ITEM_NAMES = [
    "TagKb",
  ]
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.name = read_str(data, offset, 8)
    
    self.params = read_u32(data, offset + 8)
    
    self.x_pos = read_float(data, offset + 0x0C)
    self.y_pos = read_float(data, offset + 0x10)
    self.z_pos = read_float(data, offset + 0x14)
    
    self.auxilary_param = read_u16(data, offset + 0x18)
    
    self.y_rot = read_u16(data, offset + 0x1A)
    
    self.unknown_1 = read_u16(data, offset + 0x1C)
    self.unknown_2 = read_u16(data, offset + 0x1E)
    
    self.scale_x = read_u8(data, offset + 0x20)
    self.scale_y = read_u8(data, offset + 0x21)
    self.scale_z = read_u8(data, offset + 0x22)
    self.padding = read_u8(data, offset + 0x23)
    
  def save_changes(self):
    data = self.file_entry.data
    
    write_str(data, self.offset, self.name, 8)
    
    write_u32(data, self.offset+0x08, self.params)
    
    write_float(data, self.offset+0x0C, self.x_pos)
    write_float(data, self.offset+0x10, self.y_pos)
    write_float(data, self.offset+0x14, self.z_pos)
    write_u16(data, self.offset+0x18, self.auxilary_param)
    write_u16(data, self.offset+0x1A, self.y_rot)
    
    write_u16(data, self.offset+0x1C, self.unknown_1)
    write_u16(data, self.offset+0x1E, self.unknown_2)
    
    write_u8(data, self.offset+0x20, self.scale_x)
    write_u8(data, self.offset+0x21, self.scale_y)
    write_u8(data, self.offset+0x22, self.scale_z)
    write_u8(data, self.offset+0x23, self.padding)
  
  def is_salvage(self):
    return self.name in self.SALVAGE_NAMES
  
  @property
  def salvage_type(self):
    return ((self.params & 0xF0000000) >> 28)
  
  @salvage_type.setter
  def salvage_type(self, value):
    self.params = (self.params & (~0xF0000000)) | ((value&0xF) << 28)
  
  @property
  def salvage_item_id(self):
    return ((self.params & 0x00000FF0) >> 4)
  
  @salvage_item_id.setter
  def salvage_item_id(self, value):
    self.params = (self.params & (~0x00000FF0)) | ((value&0xFF) << 4)
  
  @property
  def salvage_chart_index_plus_1(self):
    return ((self.params & 0x0FF00000) >> 20)
  
  @salvage_chart_index_plus_1.setter
  def salvage_chart_index_plus_1(self, value):
    self.params = (self.params & (~0x0FF00000)) | ((value&0xFF) << 20)
  
  @property
  def salvage_duplicate_id(self):
    return (self.unknown_1 & 0x0003)
  
  @salvage_duplicate_id.setter
  def salvage_duplicate_id(self, value):
    self.unknown_1 = (self.unknown_1 & (~0x0003)) | (value&0x0003)
  
  def is_buried_pig_item(self):
    return self.name in self.BURIED_PIG_ITEM_NAMES
  
  @property
  def buried_pig_item_id(self):
    return (self.params & 0x000000FF)
  
  @buried_pig_item_id.setter
  def buried_pig_item_id(self, value):
    self.params = (self.params & (~0x000000FF)) | (value&0xFF)

class ACTR:
  DATA_SIZE = 0x20
  
  ITEM_NAMES = [
    "item",
    "itemFLY",
  ]
  
  BOSS_ITEM_NAMES = [
    "Bitem",
  ]
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.name = read_str(data, offset, 8)
    
    self.params = read_u32(data, offset + 8)
    
    self.x_pos = read_float(data, offset + 0x0C)
    self.y_pos = read_float(data, offset + 0x10)
    self.z_pos = read_float(data, offset + 0x14)
    self.x_rot = read_u16(data, offset + 0x18)
    self.y_rot = read_u16(data, offset + 0x1A)
    
    self.set_flag = read_u16(data, offset + 0x1C)
    self.enemy_number = read_u16(data, offset + 0x1E)
  
  def save_changes(self):
    data = self.file_entry.data
    
    write_str(data, self.offset, self.name, 8)
    
    write_u32(data, self.offset+0x08, self.params)
    
    write_float(data, self.offset+0x0C, self.x_pos)
    write_float(data, self.offset+0x10, self.y_pos)
    write_float(data, self.offset+0x14, self.z_pos)
    write_u16(data, self.offset+0x18, self.x_rot)
    write_u16(data, self.offset+0x1A, self.y_rot)
    
    write_u16(data, self.offset+0x1C, self.set_flag)
    write_u16(data, self.offset+0x1E, self.enemy_number)
  
  def is_item(self):
    return self.name in self.ITEM_NAMES
  
  @property
  def item_id(self):
    return (self.params & 0x000000FF)
  
  @item_id.setter
  def item_id(self, value):
    self.params = (self.params & (~0x000000FF)) | (value&0xFF)
  
  @property
  def item_flag(self):
    return ((self.params & 0x0000FF00) >> 8)
  
  @item_flag.setter
  def item_flag(self, value):
    self.params = (self.params & (~0x0000FF00)) | ((value&0xFF) << 8)
  
  def is_boss_item(self):
    return self.name in self.BOSS_ITEM_NAMES
  
  @property
  def boss_item_stage_id(self):
    return (self.params & 0x000000FF)
  
  @boss_item_stage_id.setter
  def boss_item_stage_id(self, value):
    self.params = (self.params & (~0x000000FF)) | (value&0xFF)
  
  # The below item ID parameter did not exist for boss items in the vanilla game.
  # The randomizer adds it so that boss items can be randomized and not just always heart containers.
  @property
  def boss_item_id(self):
    return (self.params & 0x0000FF00)
  
  @boss_item_id.setter
  def boss_item_id(self, value):
    self.params = (self.params & (~0x0000FF00)) | ((value&0xFF) << 8)

class PLYR:
  DATA_SIZE = 0x20
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.name = read_str(data, offset, 8)
    
    self.event_index = read_u8(data, offset + 8)
    self.unknown1 = read_u8(data, offset + 9)
    self.spawn_type = read_u8(data, offset + 0x0A)
    self.room_num = read_u8(data, offset + 0x0B)
    
    self.x_pos = read_float(data, offset + 0x0C)
    self.y_pos = read_float(data, offset + 0x10)
    self.z_pos = read_float(data, offset + 0x14)
    self.unknown2 = read_u16(data, offset + 0x18)
    self.y_rot = read_u16(data, offset + 0x1A)
    
    self.unknown3 = read_u8(data, offset + 0x1C)
    self.spawn_id = read_u8(data, offset + 0x1D)
    self.unknown4 = read_u16(data, offset + 0x1E)
  
  def save_changes(self):
    data = self.file_entry.data
    
    write_str(data, self.offset, self.name, 8)
    
    write_u8(data, self.offset+0x08, self.event_index)
    write_u8(data, self.offset+0x09, self.unknown1)
    write_u8(data, self.offset+0x0A, self.spawn_type)
    write_u8(data, self.offset+0x0B, self.room_num)
    
    write_float(data, self.offset+0x0C, self.x_pos)
    write_float(data, self.offset+0x10, self.y_pos)
    write_float(data, self.offset+0x14, self.z_pos)
    write_u16(data, self.offset+0x18, self.unknown2)
    write_u16(data, self.offset+0x1A, self.y_rot)
    
    write_u8(data, self.offset+0x1C, self.unknown3)
    write_u8(data, self.offset+0x1D, self.spawn_id)
    write_u16(data, self.offset+0x1E, self.unknown4)

class SCLS:
  DATA_SIZE = 0xC
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.dest_stage_name = read_str(data, offset, 8)
    self.spawn_id = read_u8(data, offset+8)
    self.room_index = read_u8(data, offset+9)
    self.fade_type = read_u8(data, offset+0xA)
    self.padding = read_u8(data, offset+0xB)
  
  def save_changes(self):
    data = self.file_entry.data
    
    write_str(data, self.offset, self.dest_stage_name, 8)
    write_u8(data, self.offset+0x8, self.spawn_id)
    write_u8(data, self.offset+0x9, self.room_index)
    write_u8(data, self.offset+0xA, self.fade_type)
    write_u8(data, self.offset+0xB, self.padding)

class STAG:
  DATA_SIZE = 0x14
  
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.depth_min = read_float(data, offset)
    self.depth_max = read_float(data, offset+4)
    
    is_dungeon_and_stage_id = read_u16(data, offset+8)
    self.is_dungeon = is_dungeon_and_stage_id & 1
    self.stage_id = is_dungeon_and_stage_id >> 1
    
    self.loaded_particle_bank = read_u16(data, offset+0xA)
    self.property_index = read_u16(data, offset+0xC)
    self.unknown_1 = read_u8(data, offset+0xE)
    self.unknown_2 = read_u8(data, offset+0xF)
    self.unknown_3 = read_u8(data, offset+0x10)
    self.unknown_4 = read_u8(data, offset+0x11)
    self.draw_range = read_u16(data, offset+0x12)
  
  def save_changes(self):
    data = self.file_entry.data
    
    write_float(data, self.offset, self.depth_min)
    write_float(data, self.offset+4, self.depth_max)
    
    is_dungeon_and_stage_id = (self.stage_id << 1) | (self.is_dungeon & 1)
    write_u16(data, self.offset+8, is_dungeon_and_stage_id)
    
    write_u16(data, self.offset+0xA, self.loaded_particle_bank)
    write_u16(data, self.offset+0xC, self.property_index)
    write_u8(data, self.offset+0xE, self.unknown_1)
    write_u8(data, self.offset+0xF, self.unknown_2)
    write_u8(data, self.offset+0x10, self.unknown_3)
    write_u8(data, self.offset+0x11, self.unknown_4)
    write_u16(data, self.offset+0x12, self.draw_range)

class DummyEntry():
  def __init__(self, file_entry):
    self.file_entry = file_entry
  
  def read(self, offset):
    self.offset = offset
    data = self.file_entry.data
    
    self.raw_data_bytes = read_bytes(data, self.offset, self.DATA_SIZE)
  
  def save_changes(self):
    data = self.file_entry.data
    
    write_bytes(data, self.offset, self.raw_data_bytes)

class FILI(DummyEntry):
  DATA_SIZE = 8

class TGOB(DummyEntry):
  DATA_SIZE = 0x20

class FLOR(DummyEntry):
  DATA_SIZE = 0x14

class _2DMA(DummyEntry):
  DATA_SIZE = 0x38

class LBNK(DummyEntry):
  DATA_SIZE = 0x1

class RPAT(DummyEntry):
  DATA_SIZE = 0xC

class RPPN(DummyEntry):
  DATA_SIZE = 0x10

class SOND(DummyEntry):
  DATA_SIZE = 0x1C

class RCAM(DummyEntry):
  DATA_SIZE = 0x14

class RARO(DummyEntry):
  DATA_SIZE = 0x14

class SHIP(DummyEntry):
  DATA_SIZE = 0x10