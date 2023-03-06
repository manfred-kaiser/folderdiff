import os
import hashlib
import zipfile


def sha256sum(filename):
    hash_sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


class FileCompareResult:

    def __init__(self, removed, moved, added, modified) -> None:
        self.removed = removed
        self.moved = moved
        self.added = added
        self.modified = modified

    def print_result(self) -> None:
        if self.removed:
            print("==================== Removed =====================")
            for fileentry in sorted(self.removed, key=str.lower):
                print("- {}".format(fileentry))

        if self.moved:
            print("=========== Moved (origin -> current) ============")
            for fileentry in sorted(self.moved, key=lambda el: el[1].lower()):
                print("> {} -> {}".format(fileentry[0], fileentry[1]))

        if self.added:
            print("===================== Added ======================")
            for fileentry in sorted(self.added, key=str.lower):
                print("+ {}".format(fileentry))

        if self.modified:
            print("==================== Modified ====================")
            for fileentry in sorted(self.modified, key=str.lower):
                print("* {}".format(fileentry))

    def __bool__(self):
        return not bool(self.removed or self.moved or self.added or self.modified)


class FileCompare:

    def __init__(self, path, prefix=None) -> None:
        self.path = path
        self.prefix = prefix

    def get_hashlist(self):
        if os.path.isdir(self.path):
            return self.get_hashlist_folder()
        if os.path.isfile(self.path) and zipfile.is_zipfile(self.path):
            return self.get_hashlist_zipfile()
        raise ValueError("not supported filetype - only zip files and dirctories are supported!")

    def get_hashlist_folder(self):
        # Walk all subdirectories
        hashlist = set()
        for (directory, _, files) in os.walk(self.path):
            for f in files:
                path = os.path.join(directory, f)
                filepath = self.path
                if self.prefix and path.startswith(self.prefix.rstrip(os.sep) + os.sep):
                    filepath = os.path.join(self.path, self.prefix)
                hashlist.add((os.path.relpath(path, filepath), sha256sum(path)))
        return hashlist

    def get_hashlist_zipfile(self):
        hashlist = set()
        zfile = zipfile.ZipFile(self.path)
        zfile.testzip()
        for fileentry in zfile.namelist():
            if fileentry.endswith('/'):
                continue
            hashfunc = hashlib.sha256()
            hashfunc.update(zfile.read(fileentry))
            filepath = fileentry
            if self.prefix and fileentry.startswith(self.prefix.rstrip(os.sep) + os.sep):
                filepath = filepath[len(self.prefix.rstrip(os.sep)) + 1:]
            hashlist.add((filepath, hashfunc.hexdigest()))
        return hashlist

    def compare(self, to_compare):
        hash_set_src = self.get_hashlist()
        hash_set_dest = to_compare.get_hashlist()

        hash_set_added = {entry for entry in hash_set_dest - hash_set_src}
        hash_set_removed = {entry for entry in hash_set_src - hash_set_dest}

        hash_dict_added = {entry[1]: entry[0] for entry in hash_set_added}
        hash_dict_removed = {entry[1]: entry[0] for entry in hash_set_removed}

        moved_keys = set(hash_dict_added.keys()) & set(hash_dict_removed.keys())

        added = {e[0] for e in hash_set_added if e[1] not in moved_keys}
        moved = [(hash_dict_removed.get(key), hash_dict_added.get(key)) for key in moved_keys]
        removed = {e[0] for e in hash_set_removed if e[1] not in moved_keys}

        modified = added & removed
        added = added - modified
        removed = removed - modified

        return FileCompareResult(removed, moved, added, modified)

    def __eq__(self, to_compare):
        return bool(self.compare(to_compare))