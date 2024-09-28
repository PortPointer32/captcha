import subprocess
import os

main_process = None

def start_main():
    global main_process

    path_to_main_py = os.path.join(os.getcwd(), 'robot', 'main.py')

    # Если папка 'robot' не существует, используйте путь к main.py в текущей директории
    if not os.path.isdir(os.path.join(os.getcwd(), 'robot')):
        path_to_main_py = 'main.py'

    if main_process is not None:
        main_process.terminate()
        main_process.wait()

    cwd = 'robot' if os.path.isdir(os.path.join(os.getcwd(), 'robot')) else os.getcwd()

    main_process = subprocess.Popen(['python3', path_to_main_py], cwd=cwd)

def restart_main():
    global main_process

    path_to_main_py = os.path.join(os.getcwd(), 'robot', 'main.py')

    # Если папка 'robot' не существует, используйте путь к main.py в текущей директории
    if not os.path.isdir(os.path.join(os.getcwd(), 'robot')):
        path_to_main_py = 'main.py'

    if main_process is not None:
        main_process.terminate()
        main_process.wait()

    cwd = 'robot' if os.path.isdir(os.path.join(os.getcwd(), 'robot')) else os.getcwd()

    main_process = subprocess.Popen(['python3', path_to_main_py], cwd=cwd)
