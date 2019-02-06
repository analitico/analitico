

    # download stream to a cache file then hand over stream to file
    # the temporary file is named after the hash of the file contents in storage.
    # if we already have a file in cache with the same name, we can be assured that
    # its contents are the same as the requested file and we can serve directly from file.
    storage_file = os.path.join(self.get_cache_directory(), "cache_" + storage_obj.hash)
    if not os.path.isfile(storage_file):
        storage_temp_file = storage_file + ".tmp_" + django.utils.crypto.get_random_string()
        with open(storage_temp_file, "wb") as f:
            for b in storage_stream:
                f.write(b)
        os.rename(storage_temp_file, storage_file)
    return open(storage_file, "rb")