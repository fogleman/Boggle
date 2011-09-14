from ctypes import *

dll = None

def init(dll_path, dawg_path):
    global dll
    dll = CDLL(dll_path)
    dll.init(dawg_path)

def uninit():
    dll.uninit()

def children(letters):
    letters = ''.join(letters)
    result = create_string_buffer(32)
    dll.getChildren(result, letters, len(letters))
    return result.value

def check(letters, letter):
    letters = ''.join(letters)
    return dll.hasChild(c_char(letter), letters, len(letters))
