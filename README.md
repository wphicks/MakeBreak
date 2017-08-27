# MakeBreak

MakeBreak is a tool for saving breakpoints and other debugger information for
[lldb](https://lldb.llvm.org/) between sessions. It currently provides a
command line interface for setting persistent breakpoints. Eventually, it will
be able to save breakpoints from within the lldb interface and will provide a
plugin for vim integration.

## Basic Usage
All of the functionality of MakeBreak is currently in `make_break.py`. To set a
persistent breakpoint, run:

```bash
>> ./make_break.py break -x path/to/myExecutable mySourceFile.c 5
```
This will set a breakpoint at line 5 of mySourceFile.c when debugging
`myExecutable` (or unset it if it is already present). If the executable name is
omitted, it will default to the last executable used by MakeBreak. (The `mb
touch` command is provided to allow you to set the "last used" executable
without adding a breakpoint.) Thus, we can now simply run:

```bash
>> ./make_break.py
```

and lldb will begin debugging myExecutable with any previously set breakpoints.
To see what breakpoints have been set:

```bash
>> ./make_break.py print
mySourceFile.c:5
```

Again, -x can be used, but if omitted will default to the last touched
executable.

## Editor Integration
While I hope to create a real vim plugin to provide a convenient interface to
MakeBreak, a little tweak of your `.vimrc` can provide basic usage already.
For instance, I have `make_break.py` aliased to `mb` and the following lines in
my `.vimrc`.

```vim
function! SetDebugTarget(executable)
    silent execute '!mb touch ' . a:executable . ' > /dev/null 2>&1'
endfunction
function! ToggleBreakPoint()
    silent execute '!mb break ' . @% . ' ' . line(".") . ' > /dev/null 2>&1'
endfunction
autocmd filetype c map <F7> :call SetDebugTarget("build/%:t:r") <Left><Left>
autocmd filetype cpp map <F7> :call SetDebugTarget("build/%:t:r")<Left><Left>
nnoremap <Leader>B :call ToggleBreakPoint()<CR> :redraw!<CR>
```

If I'm editing `myExecutable.cpp`, pressing `F7` will bring up a command to set
the current MakeBreak executable. It defaults to `build/myExecutable`, but
you can change this before hitting enter. Pressing `<Leader>B` will toggle a
breakpoint at the current line. You can then run `mb` in another window, and
you will begin debugging of the selected executable with the given breakpoints.

## Contributions
Pull requests welcome! MakeBreak is licensed under GPLv3. Hack away, and
happy debugging!
