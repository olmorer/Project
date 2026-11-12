import sqlite3

GAME_FIELDS = ("title", "genre", "platform", "year", "cover", "fav", "notes")
CHAMP_FIELDS = ("name", "game_id", "date", "descr")
PERSON_FIELDS = ("name", "nick")
RESULT_FIELDS = ("champ_id", "participant_id", "place", "score")


def full_name(name, nick):
    return f"{name} ({nick})" if nick else name


class Database:
    def __init__(self):
        self.con = sqlite3.connect("gamevault.db")
        self.cur = self.con.cursor()

    def query(self, sql, args=()):
        self.cur.execute(sql, args)
        rows = self.cur.fetchall()
        self.con.commit()
        return rows

    def create_tables(self):
        self.query("CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY "
                   "KEY, title TEXT, genre TEXT, year INTEGER, cover TEXT, "
                   "platform TEXT, fav INTEGER DEFAULT 0, notes TEXT)")
        self.query("CREATE TABLE IF NOT EXISTS champs (id INTEGER PRIMARY "
                   "KEY, name TEXT, game_id INTEGER, date TEXT, descr TEXT)")
        self.query("CREATE TABLE IF NOT EXISTS participants (id INTEGER "
                   "PRIMARY KEY, name TEXT, nick TEXT)")
        self.query("CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY "
                   "KEY, champ_id INTEGER, participant_id INTEGER, "
                   "place INTEGER, score INTEGER)")

    def save(self, table, fields, data, row_id=None):
        if row_id is None:
            marks = ", ".join("?" for _ in fields)
            self.query(f"INSERT INTO {table} ({', '.join(fields)}) "
                       f"VALUES ({marks})", data)
        else:
            sets = ", ".join(f"{field} = ?" for field in fields)
            self.query(f"UPDATE {table} SET {sets} WHERE id = ?",
                       tuple(data) + (row_id,))

    def get_games(self):
        return self.query("SELECT id, title, genre, platform, fav FROM games "
                          "ORDER BY title")

    def get_game(self, game_id):
        return self.query("SELECT title, genre, platform, year, cover, fav, "
                          "notes FROM games WHERE id = ?", (game_id,))[0]

    def save_game(self, game_id, data):
        self.save("games", GAME_FIELDS, data, game_id)

    def delete_game(self, game_id):
        self.query("UPDATE champs SET game_id = NULL WHERE game_id = ?",
                   (game_id,))
        self.query("DELETE FROM games WHERE id = ?", (game_id,))

    def import_games(self, rows):
        self.cur.executemany(
            "INSERT INTO games (title, genre, year, platform, cover, fav, "
            "notes) VALUES (?, ?, ?, ?, '', 0, '')", rows)
        self.con.commit()

    def get_export_games(self):
        return self.query("SELECT title, IFNULL(genre, ''), year, "
                          "IFNULL(platform, '') FROM games ORDER BY title")

    def get_champs(self):
        return self.query("SELECT champs.id, champs.name, champs.date, "
                          "games.title FROM champs LEFT JOIN games "
                          "ON games.id = champs.game_id "
                          "ORDER BY champs.date DESC, champs.id")

    def get_champ(self, champ_id):
        return self.query("SELECT name, game_id, date, descr FROM champs "
                          "WHERE id = ?", (champ_id,))[0]

    def save_champ(self, champ_id, data):
        self.save("champs", CHAMP_FIELDS, data, champ_id)

    def delete_champ(self, champ_id):
        self.query("DELETE FROM results WHERE champ_id = ?", (champ_id,))
        self.query("DELETE FROM champs WHERE id = ?", (champ_id,))

    def get_people(self):
        return self.query("SELECT id, name, nick FROM participants "
                          "ORDER BY name")

    def save_person(self, person_id, data):
        self.save("participants", PERSON_FIELDS, data, person_id)

    def delete_person(self, person_id):
        self.query("DELETE FROM results WHERE participant_id = ?",
                   (person_id,))
        self.query("DELETE FROM participants WHERE id = ?", (person_id,))

    def get_results(self, champ_id):
        return self.query("SELECT results.id, results.place, "
                          "participants.name, participants.nick, "
                          "results.score FROM results JOIN participants "
                          "ON participants.id = results.participant_id "
                          "WHERE results.champ_id = ? "
                          "ORDER BY results.place, results.score DESC",
                          (champ_id,))

    def has_result(self, champ_id, person_id):
        return bool(self.query("SELECT id FROM results WHERE champ_id = ? "
                               "AND participant_id = ?",
                               (champ_id, person_id)))

    def save_result(self, data):
        self.save("results", RESULT_FIELDS, data)

    def delete_result(self, result_id):
        self.query("DELETE FROM results WHERE id = ?", (result_id,))

    def get_winner_rows(self, date_from, date_to, game_id):
        return self.query("SELECT champs.name, champs.date, results.place, "
                          "participants.name, participants.nick, "
                          "results.score FROM results JOIN champs "
                          "ON champs.id = results.champ_id JOIN participants "
                          "ON participants.id = results.participant_id "
                          "WHERE champs.date BETWEEN ? AND ? "
                          "AND (? IS NULL OR champs.game_id = ?) "
                          "ORDER BY champs.date DESC, champs.id, "
                          "results.place",
                          (date_from, date_to, game_id, game_id))

    def get_export_results(self):
        return self.query("SELECT champs.name, IFNULL(games.title, ''), "
                          "champs.date, participants.name, "
                          "IFNULL(participants.nick, ''), results.place, "
                          "results.score FROM results JOIN champs "
                          "ON champs.id = results.champ_id JOIN participants "
                          "ON participants.id = results.participant_id "
                          "LEFT JOIN games ON games.id = champs.game_id "
                          "ORDER BY champs.id, results.place")


db = Database()