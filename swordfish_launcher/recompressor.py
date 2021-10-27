import zipfile

def recompress(fp, compression_algorithm, compresslevel):
    endrec = zipfile._EndRecData(fp)
    endrec[]