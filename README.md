# pymaniascript
`pymaniascript` is a python-only AST builder for Maniascript scripts. This is a POC and is not meant to be used as an API for other programs. This package was made for TM2020 scripts but should be somewhat reliable with Maniaplanet ones.

## Install the package
- First, be sure to have Python installed (Python 3.9 or later is recommended). You can download it [here](https://www.python.org/downloads/).
- Create a virtual environment if you do not want this package to be installed in your main python.
- Then, clone this very repository:
```
git clone "https://github.com/MrLag31/pymaniascript"
```
- Finally, install this package inside of your python environment.
```
pip install .\pymaniascript\
```

## Main content
The main package is `pymaniascript.compiler` which is the package that compiles any script given to him. There exists a command line tool that will print the built AST and any errors/warnings the script might have generated. Due to how the game handles included files, the script needed to be compiled must be inside a pre-defined root folder, which is `Scripts` by default.

Another useful package is `pymaniascript.doch` which is handling the `doc.h` file generated by the game. It is not included by default, you will need to generate it yourself. Don't worry, there's a tool for that!

## Usage
These are directly taken from the help page of these scripts.
- `python -m pymaniascript.compiler`
```
usage: 
  python -m pymaniascript.compiler [-h] [-e] [-w] scriptfile

description:
  Computes and prints the abstract syntax tree (AST) of a maniascript script.

positional arguments:
  scriptfile  Path to your script

optional arguments:
  -h, --help  show this help message and exit
  -e          Also prints errors generated by the AST
  -w          Also prints warnings generated by the AST (forces -e)

Due to how the game handles file includes, the script needed to be compiled must be in a '/Scripts' folder.
When handling big scripts, it is preferable to redirect the output to a file:
  python -m pymaniascript.compiler [-ew] scriptfile > ast
```

- `python -m pymaniascript.doch`
```
usage: 
  python -m pymaniascript.doch [-h] exepath

description:
  Generates the 'doc.h' file from your own game. (The game must not be running)

positional arguments:
  exepath     Path to your 'Trackmania.exe' file.

optional arguments:
  -h, --help  show this help message and exit
```

## Example
Content of `./Scripts/proc1.Script.txt`:
```
#Include "MathLib" as ML

Vec2 CosSin (Real _Angle) {
    return <ML::Cos(_Angle), ML::Sin(_Angle)>;
}

main () {
    CosSin(5.);
}
```

Content of `ast` after `python -m pymaniascript.compiler -ew .\Scripts\proc1.Script.txt > ast`:
```
+ [1, 1] - [9, 2] ASTProg
| + [1, 1] - [1, 25] ASTDirectiveInclude
| | + [1, 10] - [1, 19] ASTTerminalValue: MSValue('@LITERAL')
| | + [1, 23] - [1, 25] ASTTerminal: 'ML'
| + [1, 25] - [5, 2] ASTFunctionDefinition
| | + [3, 1] - [3, 5] ASTTerminalValue: MSType('Vec2')
| | + [3, 6] - [3, 12] ASTTerminal: 'CosSin'
| | + [3, 14] - [3, 18] ASTTerminalValue: MSType('Real')
| | + [3, 19] - [3, 25] ASTTerminal: '_Angle'
| | + [3, 27] - [5, 2] ASTBlock
| | | + [4, 5] - [4, 47] ASTReturn
| | | | + [4, 12] - [4, 46] ASTVector
| | | | | + [4, 13] - [4, 28] ASTFunctionCall
| | | | | | + [4, 13] - [4, 20] ASTNamespace
| | | | | | | + [4, 13] - [4, 15] ASTTerminalValue: MSInclude('MathLib')
| | | | | | | + [4, 17] - [4, 20] ASTTerminalValue: MSFunction('Cos')
| | | | | | + [4, 21] - [4, 27] ASTTerminalValue: MSValue('_Angle')
| | | | | + [4, 30] - [4, 45] ASTFunctionCall
| | | | | | + [4, 30] - [4, 37] ASTNamespace
| | | | | | | + [4, 30] - [4, 32] ASTTerminalValue: MSInclude('MathLib')
| | | | | | | + [4, 34] - [4, 37] ASTTerminalValue: MSFunction('Sin')
| | | | | | + [4, 38] - [4, 44] ASTTerminalValue: MSValue('_Angle')
| + [7, 1] - [9, 2] ASTMain
| | + [7, 1] - [7, 1] ASTTerminalValue: MSType('Void')
| | + [7, 1] - [7, 5] ASTTerminal: 'main'
| | + [7, 9] - [9, 2] ASTBlock
| | | + [8, 5] - [8, 15] ASTFunctionCall
| | | | + [8, 5] - [8, 11] ASTTerminalValue: MSFunction('CosSin')
| | | | + [8, 12] - [8, 14] ASTTerminalValue: MSValue('@LITERAL')

proc1.Script.txt (WARNING) [8, 5] - [8, 15]: '@FUNCRESULT' will be discarded.
```

## More information about reports
When using the options `-e` or `-w` with `pymaniascript.compiler`, the compiler will generate the list of reports of the AST. They are seperated into three categories:
- `FATAL_ERROR`: The compiler stumbled on an issue it could not resolve (i.e. syntax errors or file not found).
- `ERROR`: The compiler found an error in the program that will prevent it from compiling within the game.
- `WARNING`: The compiler warns you about something you might have missed (i.e. mispelled names or discarded function results)

From the previous example, the only report is a `WARNING` stating that the returned value of `CosSin` is not used.

## Found a bug?
The correct behaviour should always be the following: every script that compiles with `pymaniascript` (i.e. without `ERROR` reports), should compile within the game and vice-versa. However, there is some known differences that makes it imperfect:
- Due to how `#Include` is handled, trying to find data inside of an uncalled namespace will result in a `FATAL_ERROR`, even within labels.
- There is no order on global definitions, which is not the case in the game.
- The variable `This` is loaded in the current scope only if `#RequireContext` is provided or if `#Extends` is used with another script that has `This`.
- You can declare functions with same signatures.

Thus, please make an issue when you find uncited differences between this compiler and the game's one.

## Special thanks
The parser/lexer was built with [sly](https://github.com/dabeaz/sly). The parser/lexer used for the `doc.h` is [robotpy-cppheaderparser](https://github.com/robotpy/robotpy-cppheaderparser). Also special thanks to cgdb from the Nadeo team who helped understand the original compiler.