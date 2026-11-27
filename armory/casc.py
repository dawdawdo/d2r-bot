"""Minimal read-only ctypes wrapper around CascLib (armory/work/libcasc.so, built by armory/build_casclib.sh).

Reads files out of D2R's CASC storage for the website's item art (Stephen OK'd reading the game files, 2026-11-27).
Never writes anything into the game folder.
"""
import ctypes as C
import os

LIB = C.CDLL(os.environ.get("CASCLIB") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "work", "libcasc.so"))
H = C.c_void_p
LIB.CascOpenStorage.argtypes = [C.c_char_p, C.c_uint32, C.POINTER(H)]
LIB.CascOpenStorage.restype = C.c_bool
LIB.CascOpenFile.argtypes = [H, C.c_void_p, C.c_uint32, C.c_uint32, C.POINTER(H)]
LIB.CascOpenFile.restype = C.c_bool
LIB.CascGetFileSize.argtypes = [H, C.POINTER(C.c_uint32)]
LIB.CascGetFileSize.restype = C.c_uint32
LIB.CascReadFile.argtypes = [H, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint32)]
LIB.CascReadFile.restype = C.c_bool
LIB.CascCloseFile.argtypes = [H]
LIB.CascCloseStorage.argtypes = [H]
LIB.GetCascError.restype = C.c_uint32


class FindData(C.Structure):
    # CASC_FIND_DATA starts with char szFileName[MAX_PATH]; the rest is skipped (oversized buffer below)
    _fields_ = [("szFileName", C.c_char * 1024), ("rest", C.c_ubyte * 4096)]


LIB.CascFindFirstFile.argtypes = [H, C.c_char_p, C.POINTER(FindData), C.c_char_p]
LIB.CascFindFirstFile.restype = H
LIB.CascFindNextFile.argtypes = [H, C.POINTER(FindData)]
LIB.CascFindNextFile.restype = C.c_bool
LIB.CascFindClose.argtypes = [H]


class Storage:
    def __init__(self, path: str):
        self.h = H()
        if not LIB.CascOpenStorage(path.encode(), 0, C.byref(self.h)):
            raise OSError(f"CascOpenStorage failed (error {LIB.GetCascError()})")

    def read(self, name: str) -> bytes:
        f = H()
        if not LIB.CascOpenFile(self.h, name.encode(), 0, 0, C.byref(f)):
            raise FileNotFoundError(f"{name} (error {LIB.GetCascError()})")
        try:
            hi = C.c_uint32(0)
            size = LIB.CascGetFileSize(f, C.byref(hi))
            buf = C.create_string_buffer(size)
            got = C.c_uint32(0)
            if not LIB.CascReadFile(f, buf, size, C.byref(got)):
                raise OSError(f"read failed: {name} (error {LIB.GetCascError()})")
            return buf.raw[: got.value]
        finally:
            LIB.CascCloseFile(f)

    def find(self, mask: str, limit: int = 100000) -> list[str]:
        fd = FindData()
        h = LIB.CascFindFirstFile(self.h, mask.encode(), C.byref(fd), None)
        out = []
        if not h:
            return out
        try:
            while True:
                out.append(fd.szFileName.decode("utf-8", "replace"))
                if len(out) >= limit or not LIB.CascFindNextFile(h, C.byref(fd)):
                    break
        finally:
            LIB.CascFindClose(h)
        return out

    def close(self):
        LIB.CascCloseStorage(self.h)
