# Compiler Project README

## Overview
This project was created for university coursework. The objective was to develop a compiler based on a provided grammar. The compiler should convert source code into low-level code that can be interpreted by a pseudo machine.

## Tools Used
- Python 3.10.12
- sly 0.5

## Usage
### Windows
python compiler.py {name_of_input_file} {name_of_output_file}

### Linux
python3 compiler.py {name_of_input_file} {name_of_output_file}

Replace `{name_of_input_file}` with the name of the input file containing the source code you want to compile, and `{name_of_output_file}` with the desired name for the output file containing the compiled low-level code.

## Example
To compile a file named `example_code.txt` into low-level code and save the output as `compiled_code.txt`, you would use the following command:

python3 compiler.py example_code.txt compiled_code.txt

## Additional Notes
- Ensure that Python 3.10.12 and the `sly` library (version 0.5) are installed on your system before using the compiler.
- Make sure to provide valid input files written in the specified language and follow any guidelines or restrictions outlined in the project requirements.

## Getting Started
To get started with the project, follow these steps:
1. Install Python 3.10.12 on your system if you haven't already. You can download it from the [official Python website](https://www.python.org/downloads/).
2. Install the `sly` library by running `pip install sly` in your terminal or command prompt.
3. Download or clone this repository to your local machine.
4. Navigate to the directory containing the `compiler.py` file.
5. Use the provided usage instructions to compile your source code files.

If you encounter any issues or have questions, please feel free to reach out for assistance.