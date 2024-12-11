from argparse import ArgumentParser
import csv
from pathlib import Path
from html import escape

# Source: https://github.com/abcd-j/data-catalog/issues/22
# Currently a custom script for the gliem_pavic dataset
# How can we generalise this?

url_root = 'https://www.ncbi.nlm.nih.gov/geo/download/'
fieldnames = ['path[POSIX]', 'size[bytes]', 'checksum[md5]', 'url']

if __name__ == "__main__":
    # Argument parsing and validation
    parser = ArgumentParser()
    parser.add_argument(
        "file_path", type=str, help="Path to file with filelist",
    )    
    parser.add_argument(
        "out_path", type=str, help="Path to output file",
    )    
    args = parser.parse_args()    

    with open(Path(args.file_path), encoding='utf8', newline='') as file:
        reader = csv.DictReader(file, delimiter='\t')
        out_rows = []
        for row in reader:
            filename = Path(row['path[POSIX]']).name
            fparts = filename.split('_')
            file_id = fparts[0]
            row['url'] = f"{url_root}?acc={file_id}&format=file&file={escape(filename)}"
            out_rows.append(row)    
    
    with open(Path(args.out_path), 'w', encoding='utf8', newline='') as output_file:
            fc = csv.DictWriter(
                output_file,
                fieldnames=fieldnames,
                delimiter='\t'
            )
            fc.writerow(dict((fn,fn) for fn in fieldnames))
            fc.writerows(out_rows)