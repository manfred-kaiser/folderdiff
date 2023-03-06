# FolderDiff


FolderDiff can be used to compare unzipped archives (e.g. Wordpress installations)
with their original zip archive or a clean source folder. 

As a result the found changes (added, deleted, moved and changed) are displayed.

## Command usage

```
$ folderdiff -h
usage: folderdiff [-h] [--prefix PREFIX] FILES FILES

folder compare tool

positional arguments:
  FILES            directory or archive to compare

options:
  -h, --help       show this help message and exit
  --prefix PREFIX  remove the profix from the source and/or destination folder
```

## Sample output

```
folderdiff wordpress-6.0.3-de_AT.zip /var/www/ --prefix wordpress/
===================== Added ======================
+ webshell.php
==================== Modified ====================
* index.php
```
