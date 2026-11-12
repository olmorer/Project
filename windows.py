import os
import sqlite3

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from db import db, full_name

DATE = "yyyy-MM-dd"


def safe(parent, func, *args):
    try:
        func(*args)
        return True
    except sqlite3.Error as error:
        QMessageBox.critical(parent, "Ошибка базы данных", str(error))
        return False


def chosen_id(parent, row, ids):
    if row < 0:
        QMessageBox.information(parent, "Выбор", "Сначала выберите строку")
        return None
    return ids[row]


def add_buttons(layout, pairs):
    for text, func in pairs:
        button = QPushButton(text)
        button.clicked.connect(func)
        layout.addWidget(button)


def make_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def fill_table(table, rows):
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            table.setItem(r, c, QTableWidgetItem(
                "" if value is None else str(value)))


def make_date(text=None):
    date = QDate.fromString(text, DATE) if text else QDate.currentDate()
    edit = QDateEdit(date)
    edit.setDisplayFormat(DATE)
    edit.setCalendarPopup(True)
    return edit


def spin(low, high, value):
    box = QSpinBox()
    box.setRange(low, high)
    box.setValue(value)
    return box


def make_box(rows, first=None):
    box = QComboBox()
    if first:
        box.addItem(first, None)
    for row in rows:
        box.addItem(row[1], row[0])
    return box


class CoverPicker(QWidget):
    def __init__(self):
        super().__init__()
        self.edit, browse = QLineEdit(), QPushButton("Выбрать...")
        browse.clicked.connect(self.choose)
        layout = QHBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(browse)

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Обложка", "", "Картинки (*.png *.jpg *.jpeg *.bmp)")
        self.edit.setText(path or self.edit.text())


def value_of(widget):
    widget = getattr(widget, "edit", widget)
    if isinstance(widget, QLineEdit):
        return widget.text().strip()
    if isinstance(widget, QTextEdit):
        return widget.toPlainText()
    if isinstance(widget, QSpinBox):
        return widget.value()
    if isinstance(widget, QCheckBox):
        return int(widget.isChecked())
    if isinstance(widget, QDateEdit):
        return widget.date().toString(DATE)
    return widget.currentData()


def set_value(widget, value):
    widget = getattr(widget, "edit", widget)
    if isinstance(widget, QLineEdit):
        widget.setText(str(value))
    elif isinstance(widget, QTextEdit):
        widget.setPlainText(value)
    elif isinstance(widget, QSpinBox):
        widget.setValue(value)
    elif isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    elif isinstance(widget, QDateEdit):
        widget.setDate(QDate.fromString(value, DATE))
    elif isinstance(widget, QComboBox):
        widget.setCurrentIndex(max(0, widget.findData(value)))


class FormDialog(QDialog):
    def __init__(self, parent, title, fields, row, save, check=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.fields, self.save, self.check = fields, save, check
        form = QFormLayout()
        for i, (label, widget) in enumerate(fields):
            form.addRow(label, widget)
            if row is not None and row[i] is not None:
                set_value(widget, row[i])
        buttons = QHBoxLayout()
        add_buttons(buttons, (("Принять", self.on_ok),
                              ("Отмена", self.reject)))
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def on_ok(self):
        values = tuple(value_of(widget) for _, widget in self.fields)
        error = None
        if values[0] in ("", None):
            error = f"Заполните поле «{self.fields[0][0].rstrip(':')}»"
        elif self.check:
            error = self.check(values)
        if error:
            QMessageBox.warning(self, "Ошибка", error)
        elif safe(self, self.save, values):
            self.accept()


def game_dialog(parent, game_id=None):
    fields = [("Название:", QLineEdit()), ("Жанр:", QLineEdit()),
              ("Платформа:", QLineEdit()), ("Год:", spin(1950, 2100, 2020)),
              ("Обложка:", CoverPicker()), ("", QCheckBox("Избранная игра")),
              ("Заметки:", QTextEdit())]
    row = db.get_game(game_id) if game_id is not None else None
    return FormDialog(parent, "Игра", fields, row,
                      lambda values: db.save_game(game_id, values),
                      lambda v: None if not v[4] or os.path.exists(v[4])
                      else "Нет такого файла обложки")


def champ_dialog(parent, champ_id=None):
    fields = [("Название:", QLineEdit()),
              ("Игра:", make_box(db.get_games(), "— без игры —")),
              ("Дата:", make_date()), ("Описание:", QTextEdit())]
    row = db.get_champ(champ_id) if champ_id is not None else None
    return FormDialog(parent, "Чемпионат", fields, row,
                      lambda values: db.save_champ(champ_id, values))


def person_dialog(parent, person_id=None):
    fields = [("Имя:", QLineEdit()), ("Никнейм:", QLineEdit())]
    row = next((p[1:] for p in db.get_people() if p[0] == person_id), None)
    return FormDialog(parent, "Участник", fields, row,
                      lambda values: db.save_person(person_id, values))


def result_dialog(parent, champ_id):
    people = [(p[0], full_name(p[1], p[2])) for p in db.get_people()]
    fields = [("Участник:", make_box(people)), ("Место:", spin(1, 999, 1)),
              ("Очки:", spin(0, 100000, 0))]

    return FormDialog(parent, "Результат", fields, None,
                      lambda values: db.save_result((champ_id,) + values),
                      lambda v: "Участник уже есть в чемпионате"
                      if db.has_result(champ_id, v[0]) else None)


class ResultsWindow(QDialog):
    def __init__(self, parent, champ_id, name):
        super().__init__(parent)
        self.champ_id, self.ids = champ_id, []
        self.setWindowTitle("Результаты: " + name)
        self.table = make_table(["Место", "Участник", "Никнейм", "Очки"])
        buttons = QHBoxLayout()
        add_buttons(buttons, (("Добавить", self.add),
                              ("Удалить", self.delete),
                              ("Закрыть", self.accept)))
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self.load()

    def load(self):
        rows = db.get_results(self.champ_id)
        self.ids = [row[0] for row in rows]
        fill_table(self.table, [row[1:] for row in rows])

    def add(self):
        if result_dialog(self, self.champ_id).exec():
            self.load()

    def delete(self):
        result_id = chosen_id(self, self.table.currentRow(), self.ids)
        if result_id is not None and safe(self, db.delete_result, result_id):
            self.load()


class BarChart(QWidget):
    def __init__(self):
        super().__init__()
        self.bars = []
        self.setMinimumHeight(220)

    def set_data(self, bars):
        self.bars = bars[:10]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.bars:
            return painter.drawText(10, 20, "Нет данных")
        top = max(value for _, value in self.bars) or 1
        width = self.width() // len(self.bars)
        for i, (name, value) in enumerate(self.bars):
            bar = int((self.height() - 50) * value / top)
            x, y = i * width + 5, self.height() - 30 - bar
            painter.fillRect(x, y, width - 10, bar, QColor("#3d5afe"))
            painter.drawText(x, y - 5, str(value))
            painter.drawText(x, self.height() - 10, name[:12])


class WinnersWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Победители и рейтинги")
        self.resize(720, 620)
        self.mode_box = QComboBox()
        self.mode_box.addItems(["Победители и призёры", "Призовые места",
                                "Сумма очков"])
        self.places_spin = spin(1, 50, 3)
        self.game_box = make_box(db.get_games(), "Все игры")
        self.date_from = make_date("2000-01-01")
        self.date_to = make_date("2030-12-31")
        self.table = make_table([])
        self.chart = BarChart()
        show_button = QPushButton("Показать")
        show_button.clicked.connect(self.show_data)
        top, filters = QHBoxLayout(), QHBoxLayout()
        for widget in (QLabel("Режим:"), self.mode_box, QLabel("Места до:"),
                       self.places_spin, show_button):
            top.addWidget(widget)
        for widget in (QLabel("Игра:"), self.game_box, QLabel("С:"),
                       self.date_from, QLabel("По:"), self.date_to):
            filters.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(filters)
        layout.addWidget(self.table)
        layout.addWidget(self.chart)
        self.show_data()

    def show_data(self):
        mode = self.mode_box.currentIndex()
        limit = self.places_spin.value()
        rows = db.get_winner_rows(self.date_from.date().toString(DATE),
                                  self.date_to.date().toString(DATE),
                                  self.game_box.currentData())
        totals, table_rows = {}, []
        for champ, date, place, name, nick, score in rows:
            who = full_name(name, nick)
            if mode == 2:
                totals[who] = totals.get(who, 0) + score
            elif place <= limit:
                totals[who] = totals.get(who, 0) + 1
                table_rows.append([champ, date, place, who, score])
        ranking = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        headers = ["Чемпионат", "Дата", "Место", "Участник", "Очки"]
        if mode:
            headers = ["Участник", ["Призовых мест", "Сумма очков"][mode - 1]]
            table_rows = [[who, value] for who, value in ranking]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        fill_table(self.table, table_rows)
        self.chart.set_data(ranking)