from os import path, spawnv, P_WAIT
import argparse

parser = argparse.ArgumentParser(prog='\n  python -m pymaniascript.doch',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='description:\n  Generates the \'doc.h\' file from your own game. (The game must not be running)')

parser.add_argument('exepath', help='Path to your \'Trackmania.exe\' file.')
args = parser.parse_args()

filepath = args.exepath

full_filepath = path.abspath(filepath)
if not path.isfile(full_filepath) or not full_filepath.endswith('Trackmania.exe'):
    print('You must provide a path to the executable!')
    exit()

else:
    cur_file = path.abspath(__file__)
    doch_target = path.join(path.split(cur_file)[0], 'doc.h')
    spawnv(P_WAIT, full_filepath, [str(full_filepath), f'/generatescriptdoc="{doch_target}"'])