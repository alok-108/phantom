" Phantom syntax highlighting for Python files.
" Load the standard Python syntax first.
if exists("b:current_syntax")
  finish
endif

runtime! syntax/python.vim
unlet! b:current_syntax


" Phantom instruction keywords.
syntax match phantomInstruction /\<event\.declare\>/
syntax match phantomInstruction /\<event\.on\>/
syntax match phantomInstruction /\<diagnostic\.note\>/
syntax match phantomInstruction /\<diagnostic\.warn\>/
syntax match phantomInstruction /\<counter\.create\>/
syntax match phantomInstruction /\<counter\.increment\>/
syntax match phantomInstruction /\<counter\.decrement\>/
syntax match phantomInstruction /\<counter\.reset\>/
syntax match phantomInstruction /\<meta\.author\>/
syntax match phantomInstruction /\<meta\.version\>/
syntax match phantomInstruction /\<meta\.license\>/
syntax match phantomInstruction /\<meta\.tags\>/
" Phantom markers.
syntax match phantomMarker /^\s*#:\s*ws:begin.*$/
syntax match phantomMarker /^\s*#:\s*ws:end.*$/
syntax match phantomMarker /^\s*#:\s*zw:begin.*$/
syntax match phantomMarker /^\s*#:\s*zw:end.*$/
syntax match phantomMarker /^\s*#:\s*phantom:hybrid.*$/

" Phantom version header.
syntax match phantomHeader /^\s*#:\s*phantom:\d\+\.\d\+\.\d\+.*$/
" Highlight groups.
highlight default link phantomInstruction Special
highlight default link phantomMarker PreProc
highlight default link phantomHeader PreProc
let b:current_syntax = "phantom"