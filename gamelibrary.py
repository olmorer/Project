import csv
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QTabWidget, QVBoxLayout, QWidget)

from db import db
from windows import (
    ResultsWindow, WinnersWindow, add_buttons, champ_dialog, chosen_id,
    fill_table, game_dialog, make_table, person_dialog, safe)


class GameLibrary(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Library")
        self.game_ids, self.champ_ids, self.person_ids = [], [], []
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.make_games_tab()
        self.make_champs_tab()
        self.make_people_tab()
        self.make_menu()
        self.refresh_all()

    def refresh_all(self):
        self.load_games()
        self.load_champs()
        self.load_people()

    def crud(self, widget, ids, dialog, reload, question, delete):
        return (
            ("Добавить", lambda: self.open_item(True, widget, ids, dialog,
                                                reload)),
            ("Изменить", lambda: self.open_item(False, widget, ids, dialog,
                                                reload)),
            ("Удалить", lambda: self.remove_item(widget, ids, question,
                                                 delete, reload)))

    def open_item(self, new, widget, ids, dialog, reload):
        item_id = None
        if not new:
            item_id = chosen_id(self, widget.currentRow(), getattr(self, ids))
            if item_id is None:
                return
        if dialog(self, item_id).exec():
            reload()

    def remove_item(self, widget, ids, question, delete, reload):
        item_id = chosen_id(self, widget.currentRow(), getattr(self, ids))
        if item_id is None:
            return
        answer = QMessageBox.question(self, "Подтверждение", question)
        if answer == QMessageBox.StandardButton.Yes and safe(self, delete,
                                                             item_id):
            reload()

    def add_tab(self, title, widget, pairs):
        buttons = QHBoxLayout()
        add_buttons(buttons, pairs)
        layout = QVBoxLayout()
        layout.addWidget(widget)
        layout.addLayout(buttons)
        tab = QWidget()
        tab.setLayout(layout)
        self.tabs.addTab(tab, title)

    def make_games_tab(self):
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.load_games)
        self.games_list = QListWidget()
        self.games_list.currentRowChanged.connect(self.show_game)
        self.cover_label = QLabel("Обложка")
        self.cover_label.setFixedSize(150, 150)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        pairs = self.crud(self.games_list, "game_ids", game_dialog,
                          self.refresh_all, "Удалить игру?", db.delete_game)
        right = QVBoxLayout()
        right.addWidget(self.cover_label)
        right.addWidget(self.info_label)
        add_buttons(right, pairs)
        right.addStretch()
        left = QVBoxLayout()
        left.addWidget(self.search_edit)
        left.addWidget(self.games_list)
        main = QHBoxLayout()
        main.addLayout(left, 2)
        main.addLayout(right, 1)
        tab = QWidget()
        tab.setLayout(main)
        self.tabs.addTab(tab, "Игры")

    def load_games(self):
        text = self.search_edit.text().strip().lower()
        self.games_list.clear()
        self.game_ids = []
        for gid, title, genre, platform, fav in db.get_games():
            values = (title, genre or "", platform or "")
            if any(text in value.lower() for value in values):
                self.games_list.addItem(("★ " if fav else "") + title)
                self.game_ids.append(gid)
        self.statusBar().showMessage(f"Игр: {len(self.game_ids)}")

    def show_game(self):
        row = self.games_list.currentRow()
        if row < 0:
            self.cover_label.setText("Обложка")
            self.info_label.setText("")
            return
        title, genre, platform, year, cover, fav, notes = db.get_game(
            self.game_ids[row])
        self.info_label.setText(
            f"{title}\nЖанр: {genre or '—'}\nПлатформа: {platform or '—'}\n"
            f"Год: {year}\n{'★ Избранное' if fav else ''}\n"
            f"Заметки: {notes or '—'}")
        pixmap = QPixmap(cover or "")
        if pixmap.isNull():
            self.cover_label.setText("Нет обложки")
        else:
            small = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
            self.cover_label.setPixmap(small)

    def make_champs_tab(self):
        self.champs_list = QListWidget()
        self.champs_list.itemDoubleClicked.connect(self.open_results)
        pairs = self.crud(self.champs_list, "champ_ids", champ_dialog,
                          self.load_champs,
                          "Удалить чемпионат вместе с результатами?",
                          db.delete_champ)
        self.add_tab("Чемпионаты", self.champs_list, pairs
                     + (("Результаты...", self.open_results),))

    def load_champs(self):
        self.champs_list.clear()
        self.champ_ids = []
        for cid, name, date, game in db.get_champs():
            self.champs_list.addItem(f"{name} — {game or 'без игры'} ({date})")
            self.champ_ids.append(cid)

    def open_results(self):
        champ_id = chosen_id(self, self.champs_list.currentRow(),
                             self.champ_ids)
        if champ_id is not None:
            name = db.get_champ(champ_id)[0]
            ResultsWindow(self, champ_id, name).exec()

    def make_people_tab(self):
        self.people_table = make_table(["Имя", "Никнейм"])
        pairs = self.crud(self.people_table, "person_ids", person_dialog,
                          self.load_people,
                          "Удалить участника вместе с результатами?",
                          db.delete_person)
        self.add_tab("Участники", self.people_table, pairs)

    def load_people(self):
        people = db.get_people()
        self.person_ids = [row[0] for row in people]
        fill_table(self.people_table,
                   [[name, nick] for _, name, nick in people])

    def make_menu(self):
        file_menu = self.menuBar().addMenu("Файл")
        file_menu.addAction("Импорт игр из CSV...", self.import_games)
        file_menu.addAction("Экспорт игр в CSV...", self.export_games)
        file_menu.addAction("Экспорт результатов в CSV...",
                            self.export_results)
        file_menu.addAction("Выход", self.close)
        self.menuBar().addMenu("Статистика").addAction(
            "Победители и рейтинги...", lambda: WinnersWindow(self).exec())
        self.menuBar().addMenu("Справка").addAction(
            "О программе", lambda: QMessageBox.about(self, "О программе",
                                                     "Game Library"))

    def import_games(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт", "",
                                              "CSV (*.csv)")
        if path == "":
            return
        try:
            with open(path, encoding="utf-8-sig", newline="") as file:
                delimiter = ";" if ";" in file.readline() else ","
                file.seek(0)
                rows = [(r["title"], r.get("genre") or "",
                         int(r.get("year") or 0), r.get("platform") or "")
                        for r in csv.DictReader(file, delimiter=delimiter)
                        if r.get("title")]
            db.import_games(rows)
        except (OSError, csv.Error, KeyError, ValueError,
                UnicodeDecodeError) as error:
            return QMessageBox.critical(self, "Ошибка импорта", str(error))
        self.refresh_all()
        self.statusBar().showMessage(f"Импортировано игр: {len(rows)}")

    def export_games(self):
        self.write_csv("games.csv", ["title", "genre", "year", "platform"],
                       db.get_export_games())

    def export_results(self):
        header = ["champ", "game", "date", "participant", "nick", "place",
                  "score"]
        self.write_csv("results.csv", header, db.get_export_results())

    def write_csv(self, name, header, rows):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт", name,
                                              "CSV (*.csv)")
        if path == "":
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as file:
                csv.writer(file).writerows([header] + rows)
        except OSError as error:
            return QMessageBox.critical(self, "Ошибка записи", str(error))
        self.statusBar().showMessage(f"Записано строк: {len(rows)}")


if __name__ == "__main__":
    db.create_tables()
    app = QApplication(sys.argv)
    window = GameLibrary()
    window.show()
    sys.exit(app.exec())