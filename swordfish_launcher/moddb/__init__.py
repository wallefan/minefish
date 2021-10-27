import sqlite3

class ModDB:
    def __init__(self, db: sqlite3.Connection):
        self.cursor = db.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS mod2jar(modid TEXT, modver, jar_mdbid INTEGER PRIMARY KEY)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS downloads(mdbid INTEGER PRIMARY KEY, technicMD5,'
                            'technicURL, curseforge_projID INTEGER, curseforge_fileID INTEGER, filename TEXT NOT NULL)')

    def lookup_curseforge(self, numid):
        return ['https://media.forgecdn.net/%d/%d/%s' % self.cursor.execute('SELECT curseforge_projid, curseforge_fileID, filename FROM downloads WHERE mdbid=?', (numid,)).fetchone() for numid in numids]