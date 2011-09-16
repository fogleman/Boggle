from ctypes import *

dll = None

def init(dll_path, dawg_path):
    global dll
    dll = CDLL(dll_path)
    dll.init(dawg_path)

def uninit():
    dll.uninit()

def is_word(letters):
    letters = str(letters)
    return bool(dll.is_word('%s$' % letters))

def get_children(letters):
    letters = str(''.join(letters))
    result = create_string_buffer(32)
    dll.get_children(result, letters)
    return result.value

def has_child(letters, letter):
    letters = str(''.join(letters))
    letter = str(letter)
    return bool(dll.has_child(letters, c_char(letter)))

def find(grid, letters):
    grid = str(grid)
    letters = str(letters)
    return bool(dll.find(grid, letters))
