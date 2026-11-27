#!/bin/bash
# Build CascLib (read-only access to Blizzard's CASC game archives) as armory/work/libcasc.so for armory/icons.py.
# Linux (GLaDOS) only; needs git, gcc and g++. CascLib bundles its own zlib. Pinned to the commit tested 2026-11-27.
set -euo pipefail
cd "$(dirname "$0")/work"
REV=6b889ec
[ -d casclib ] || git clone -q https://github.com/ladislav-zezula/CascLib.git casclib
git -C casclib checkout -q "$REV"
cd casclib && mkdir -p build
D="-DCASCLIB_NO_AUTO_LINK_LIBRARY -DCASCLIB_NODEBUG"
for f in src/jenkins/lookup3.c src/zlib/{adler32,crc32,inffast,inflate,inftrees,zutil}.c; do
  gcc -c -O2 -fPIC -w $D "$f" -o "build/$(basename "$f").o"
done
for f in src/common/{Common,Directory,Csv,FileStream,FileTree,ListFile,Mime,RootHandler,Sockets}.cpp \
         src/hashes/{md5,sha1}.cpp src/overwatch/{apm,cmf,aes}.cpp \
         src/Casc{Decompress,Decrypt,DumpData,Files,FindFile,IndexFiles,OpenFile,OpenStorage,ReadFile}.cpp \
         src/CascRootFile_{Diablo3,Install,MNDX,Text,TVFS,OW,WoW}.cpp; do
  g++ -c -O2 -fPIC -w -std=c++17 $D "$f" -o "build/$(basename "$f").o"
done
g++ -shared -o ../libcasc.so build/*.o -lpthread
echo "built $(cd .. && pwd)/libcasc.so"
