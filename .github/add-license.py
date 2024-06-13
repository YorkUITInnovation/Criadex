from pathlib import Path

words = """\"\"\"

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Isaac Kogan
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

\"\"\"

"""

# Path to the directory where you want to start
root_dir = Path('../app')

# Variable to be added
d = 0


def update_dir(dir_path: Path):
    # Loop through all .py files in the directory and subdirectories
    for filepath in root_dir.rglob('*.py'):

        if "rewrite" in filepath.name:
            continue

        # Read the content of the file
        with open(filepath, 'r') as file:
            content = file.read()

        if words.strip() in content:
            continue

        # Add the variable declaration to the top of the file content
        new_content = words + content

        with open(filepath, 'w') as file:
            file.write(new_content)

        print(f"Updated {filepath}")


if __name__ == '__main__':
    update_dir(dir_path=Path("../app"))
    update_dir(dir_path=Path("../criadex"))
