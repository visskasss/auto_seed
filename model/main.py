# -*- coding: utf-8 -*-
"""Визуализация посева в кассеты (Pygame). Запуск: python posev.py
Управление: ПРОБЕЛ пауза, ↑/↓ скорость, R заново, ESC выход.

Как устроена установка в этой модели:
  * дозатор висит на балке и ездит только влево-вправо (ось X);
  * кассеты по очереди подъезжают к балке сами и сдвигаются на один ряд вперёд (ось Y);
  * шестерёнка в дозаторе: 6 лунок, за каждую подачу поворачивается на 30°.
"""
import math
import pygame

# ---------- параметры ----------
ROWS, COLS = 4, 6
POCKETS, STEP_DEG = 6, 60
CELL = 56                          # пикселей между центрами ячеек (в жизни 40 мм)

CARDS = [["111011", "101101", "110011", "111110"],     # карта кассеты 1 (1 = сеять)
         ["101010", "010101", "101010", "010101"]]     # карта кассеты 2

# Игрушечные отказы: (кассета, ряд, столбец, попытка) -> "пусто" или "два"
FAULTS = {(0, 1, 3, 1): "пусто", (0, 2, 4, 1): "два", (1, 2, 4, 1): "пусто"}

# экран
CASS_X = 200                       # левый край кассеты
DROP_Y = 340                       # на этой высоте дозатор роняет шарик
HOME_X = 70                        # концевик дозатора слева
OY_START, OY_END = 720, -300       # кассета подъезжает снизу и уезжает вверх


def row_oy(r):
    """Положение кассеты (верхний край), когда под балкой ряд r. Ряд 1 заезжает первым."""
    return DROP_Y - 30 - (r - 1) * CELL


def col_x(c):
    return CASS_X + 30 + (c - 1) * CELL


# ---------- СЦЕНАРИЙ: сюда потом подставить разбор логов Arduino ----------
def get_steps():
    """Каждый шаг — словарь: text (по-русски), dur (с) и что делается:
    oy — куда едет кассета, hx — куда едет дозатор, feed — подача (сколько шариков выпало),
    cell — какая ячейка активна, set — что записать в ячейку после шага, color — цвет плашки."""
    st = []
    for k, card in enumerate(CARDS):
        st.append(dict(text=f"Кассета {k + 1} подъезжает к балке", dur=1.6, k=k, color="blue",
                       oy_from=OY_START, oy=row_oy(1), queue=len(CARDS) - k - 1))
        st.append(dict(text="Дозатор едет к концевику: ищем ноль", dur=1.2, hx=HOME_X, color="blue"))
        for r in range(1, ROWS + 1):
            if r > 1:
                st.append(dict(text=f"Кассета сдвигается: под балкой ряд {r}", dur=0.8, oy=row_oy(r), color="blue"))
            cols = [c for c in range(1, COLS + 1) if card[r - 1][c - 1] == "1"]
            for c in cols:
                st.append(dict(text=f"Дозатор едет к столбцу {c} (ряд {r})", dur=0.7, hx=col_x(c),
                               cell=(r, c), color="blue"))
                for attempt in (1, 2, 3):
                    fault = FAULTS.get((k, r, c, attempt))
                    balls = {None: 1, "пусто": 0, "два": 2}[fault]
                    st.append(dict(text=f"Подача: шестерёнка поворачивается на {STEP_DEG}°", dur=1.5, feed=balls,
                                   color="blue"))
                    if fault is None:
                        st.append(dict(text="Проверка: шарик в ячейке, всё хорошо", dur=0.7,
                                       set=(r, c, 1), color="green"))
                        break
                    if fault == "пусто":
                        st.append(dict(text="Проверка: в ячейке пусто, подаём ещё раз", dur=1.0, color="amber"))
                    else:
                        st.append(dict(text="СТОП: в ячейке два шарика! Оператор убирает лишний", dur=2.0,
                                       set=(r, c, 2), color="red"))
                        st.append(dict(text="Ячейка очищена, подаём ещё раз", dur=0.8, set=(r, c, 0), color="amber"))
        st.append(dict(text=f"Кассета {k + 1} готова и уезжает", dur=1.6, oy=OY_END, hx=HOME_X, color="green"))
    st.append(dict(text="Посев закончен", dur=3.0, color="green"))
    return st


# ---------- цвета (светлая тема) ----------
COL = dict(bg=(232, 240, 252), card=(255, 255, 255), border=(190, 205, 225), text=(30, 41, 59),
           mute=(100, 116, 139), blue=(25, 118, 210), green=(34, 160, 80), amber=(245, 158, 11),
           red=(220, 38, 38), ball=(255, 112, 67), cass=(255, 236, 179), cass_edge=(245, 190, 60),
           hole=(255, 255, 255), ring=(148, 163, 184), gear=(187, 222, 251), steel=(148, 163, 184))
TINT = dict(blue=(227, 242, 253), green=(228, 247, 234), amber=(255, 243, 214), red=(254, 226, 226))

# правая панель (вид сбоку)
GX, GY, GR = 920, 290, 85          # центр и радиус шестерёнки
WIN_Y = GY + GR - 5                # окно выдачи
FLOOR_Y = 548                      # дно ячейки в разрезе


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1120, 700))
        pygame.display.set_caption("Роботизированный посев")
        path = pygame.font.match_font("dejavusans,segoeui,arial,liberationsans")
        self.f_big = pygame.font.Font(path, 28)
        self.f_med = pygame.font.Font(path, 18)
        self.f = pygame.font.Font(path, 16)
        self.f_small = pygame.font.Font(path, 13)
        self.steps = get_steps()
        self.speed, self.paused = 1.0, False
        self.reset()

    # ---------- состояние ----------
    def reset(self):
        self.i = 0
        self.k = 0
        self.queue = len(CARDS) - 1
        self.cells = [[[0] * COLS for _ in range(ROWS)] for _ in CARDS]
        self.oy, self.hx = OY_START, HOME_X
        self.angle = 0.0
        self.cell = None
        self.landed = 0
        self.retries = 0
        self.log = []
        self.begin()

    def begin(self):
        s = self.steps[self.i]
        self.t = 0.0
        if "oy_from" in s:
            self.oy = s["oy_from"]
        self.oy0, self.hx0, self.angle0 = self.oy, self.hx, self.angle
        if "k" in s:
            self.k, self.queue = s["k"], s["queue"]
        if "cell" in s:
            self.cell = s["cell"]
        if "feed" in s:
            self.landed = 0
            a_end = self.angle0 + STEP_DEG       # какая лунка окажется у окна выдачи
            self.release = min(range(POCKETS), key=lambda i: abs((a_end + i * 360 / POCKETS) % 360 - 180))
        if s["text"].startswith("Проверка: в ячейке пусто") or s["text"].startswith("Ячейка очищена"):
            self.retries += 1
        self.log = (self.log + [s["text"]])[-3:]

    def finish(self):
        s = self.steps[self.i]
        if "oy" in s:
            self.oy = s["oy"]
        if "hx" in s:
            self.hx = s["hx"]
        if "feed" in s:
            self.angle = self.angle0 + STEP_DEG
            self.landed = s["feed"]
        if "set" in s:
            r, c, v = s["set"]
            self.cells[self.k][r - 1][c - 1] = v
            self.landed = v
        if self.i + 1 < len(self.steps):
            self.i += 1
            self.begin()
        else:
            self.paused = True

    def update(self, dt):
        if not self.paused:
            self.t += dt * self.speed
            if self.t >= self.steps[self.i]["dur"]:
                self.finish()

    def p(self):
        return min(1.0, self.t / self.steps[self.i]["dur"])

    @staticmethod
    def ease(p):
        return p * p * (3 - 2 * p)

    def cur_oy(self):
        s = self.steps[self.i]
        return self.oy0 + (s["oy"] - self.oy0) * self.ease(self.p()) if "oy" in s else self.oy

    def cur_hx(self):
        s = self.steps[self.i]
        return self.hx0 + (s["hx"] - self.hx0) * self.ease(self.p()) if "hx" in s else self.hx

    def cur_angle(self):
        if "feed" in self.steps[self.i]:
            return self.angle0 + STEP_DEG * self.ease(min(1.0, self.p() / 0.4))
        return self.angle

    # ---------- рисование ----------
    def text(self, s, pos, font=None, color="text", anchor="topleft"):
        img = (font or self.f).render(s, True, COL[color])
        self.screen.blit(img, img.get_rect(**{anchor: pos}))

    def box(self, rect, fill="card", border="border", r=12):
        pygame.draw.rect(self.screen, COL.get(fill) or TINT[fill], rect, 0, r)
        pygame.draw.rect(self.screen, COL[border], rect, 2, r)

    def draw_cassette(self):
        oy, k = self.cur_oy(), self.k
        pygame.draw.rect(self.screen, COL["cass"], (CASS_X, oy, COLS * CELL, ROWS * CELL), 0, 10)
        pygame.draw.rect(self.screen, COL["cass_edge"], (CASS_X, oy, COLS * CELL, ROWS * CELL), 3, 10)
        for r in range(1, ROWS + 1):
            cy = int(oy + 28 + (r - 1) * CELL)
            self.text(str(r), (CASS_X - 14, cy), self.f_small, "mute", "center")
            for c in range(1, COLS + 1):
                cx = int(col_x(c))
                want = CARDS[k][r - 1][c - 1] == "1"
                v = self.cells[k][r - 1][c - 1]
                ring = COL["blue"] if want else COL["ring"]
                if v == 1:
                    ring = COL["green"]
                elif v == 2:
                    ring = COL["red"]
                pygame.draw.circle(self.screen, COL["hole"], (cx, cy), 22)
                pygame.draw.circle(self.screen, ring, (cx, cy), 22, 3)
                if v >= 1:
                    dx = 6 if v == 2 else 0
                    pygame.draw.circle(self.screen, COL["ball"], (cx - dx, cy), 9)
                    if v == 2:
                        pygame.draw.circle(self.screen, COL["ball"], (cx + dx, cy), 9)
                if not want:
                    pygame.draw.line(self.screen, COL["ring"], (cx - 7, cy), (cx + 7, cy), 3)
        if self.cell and "oy" not in self.steps[self.i]:
            r, c = self.cell
            pygame.draw.circle(self.screen, COL["amber"], (int(col_x(c)), int(oy + 28 + (r - 1) * CELL)), 27, 4)

    def draw_beam(self):
        hx = int(self.cur_hx())
        pygame.draw.rect(self.screen, COL["steel"], (40, 255, 680, 10), 0, 4)             # балка
        pygame.draw.rect(self.screen, COL["green"], (40, 247, 14, 26), 0, 3)              # концевик
        pygame.draw.rect(self.screen, COL["blue"], (hx - 28, 265, 56, 46), 0, 8)          # дозатор
        pygame.draw.rect(self.screen, COL["card"], (hx - 6, 311, 12, 22), 0, 3)           # носик
        pygame.draw.rect(self.screen, COL["blue"], (hx - 6, 311, 12, 22), 2, 3)
        s = self.steps[self.i]
        if "feed" in s and self.p() > 0.5 and s["feed"] > 0:                               # шарик упал
            q = (self.p() - 0.5) / 0.5
            pygame.draw.circle(self.screen, COL["amber"], (hx, DROP_Y), int(8 + 22 * q), 3)

    def draw_sidebar(self):
        k = self.k
        need = sum(ch == "1" for row in CARDS[k] for ch in row)
        done = sum(v == 1 for row in self.cells[k] for v in row)
        self.text(f"Кассета {k + 1} из {len(CARDS)}", (34, 104), self.f_med)
        self.text(f"Посеяно: {done} из {need}", (34, 134))
        self.text(f"Повторов: {self.retries}", (34, 160))
        self.text(f"В очереди: {self.queue}", (34, 186))
        self.text("концевик", (34, 280), self.f_small, "mute")
        y = 380
        for ring, label in (("blue", "надо сеять"), ("green", "шарик есть"), ("red", "два шарика"), ("ring", "не сеять")):
            pygame.draw.circle(self.screen, COL["hole"], (50, y), 11)
            pygame.draw.circle(self.screen, COL[ring], (50, y), 11, 3)
            self.text(label, (70, y), self.f_small, "text", "midleft")
            y += 32

    def draw_side_view(self):
        s = self.steps[self.i]
        self.box((740, 90, 360, 600))
        self.text("Дозатор, вид сбоку", (760, 104), self.f_med)
        # бункер
        pygame.draw.polygon(self.screen, COL["steel"], [(860, 140), (980, 140), (935, GY - GR), (905, GY - GR)], 3)
        for bx, by in ((895, 160), (920, 160), (945, 160), (907, 182), (932, 182), (920, 200)):
            pygame.draw.circle(self.screen, COL["ball"], (bx, by), 10)
        self.text("бункер", (1000, 150), self.f_small, "mute")
        # шестерёнка
        a = self.cur_angle()
        pygame.draw.circle(self.screen, COL["gear"], (GX, GY), GR)
        pygame.draw.circle(self.screen, COL["blue"], (GX, GY), GR, 4)
        feed = s.get("feed")
        p = self.p()
        for i in range(POCKETS):
            th = math.radians(a + i * 360 / POCKETS)
            px, py = int(GX + 58 * math.sin(th)), int(GY - 58 * math.cos(th))
            pygame.draw.circle(self.screen, COL["hole"], (px, py), 17)
            pygame.draw.circle(self.screen, COL["blue"], (px, py), 17, 2)
            hidden = feed is not None and i == self.release and (feed == 0 or p >= 0.4)
            if not hidden:
                pygame.draw.circle(self.screen, COL["ball"], (px, py), 12)
        pygame.draw.circle(self.screen, COL["blue"], (GX, GY), 9)
        self.text("угол", (760, 262), self.f_small, "mute")
        self.text(f"{a:.0f}°", (760, 280), self.f_med)
        self.text(f"шаг {STEP_DEG}°", (760, 310), self.f_small, "mute")
        # выходная трубка и ячейка кассеты в разрезе
        pygame.draw.line(self.screen, COL["steel"], (GX - 14, WIN_Y), (GX - 14, 470), 3)
        pygame.draw.line(self.screen, COL["steel"], (GX + 14, WIN_Y), (GX + 14, 470), 3)
        self.text("выдача", (945, 400), self.f_small, "mute")
        self.text("зазор 10–15 мм", (945, 480), self.f_small, "mute")
        pygame.draw.rect(self.screen, COL["cass"], (840, 500, 160, 80), 0, 6)
        pygame.draw.rect(self.screen, COL["hole"], (880, 500, 80, 62))
        pygame.draw.rect(self.screen, COL["cass_edge"], (840, 500, 160, 80), 3, 6)
        self.text("ячейка кассеты", (GX, 600), self.f_small, "mute", "midtop")
        # шарики, лежащие в ячейке
        if self.landed >= 1:
            xs = [GX] if self.landed == 1 else [GX - 15, GX + 15]
            for x in xs:
                pygame.draw.circle(self.screen, COL["ball"], (x, FLOOR_Y), 12)
        # падающие шарики
        if feed:
            for n in range(feed):
                pp = p - 0.12 * n
                if pp < 0.4:
                    continue
                if pp < 0.5 and n == 0:     # из лунки в окно
                    th = math.radians(self.angle0 + STEP_DEG + self.release * 360 / POCKETS)
                    x0, y0 = GX + 58 * math.sin(th), GY - 58 * math.cos(th)
                    q = (pp - 0.4) / 0.1
                    x, y = x0 + (GX - x0) * q, y0 + (WIN_Y - y0) * q
                else:
                    q = min(1.0, max(0.0, (pp - 0.5) / 0.5))
                    x, y = GX + (15 * (n * 2 - 1) if feed == 2 else 0) * q, WIN_Y + (FLOOR_Y - WIN_Y) * q * q
                pygame.draw.circle(self.screen, COL["ball"], (int(x), int(y)), 12)

    def draw(self):
        s = self.steps[self.i]
        self.screen.fill(COL["bg"])
        # левая панель: балка, дозатор, кассета (обрезаем по рамке: кассета выезжает «из-за края»)
        self.box((20, 90, 705, 470))
        self.screen.set_clip((22, 92, 701, 466))
        self.draw_cassette()
        self.draw_beam()
        self.screen.set_clip(None)
        self.draw_sidebar()
        self.draw_side_view()
        # журнал
        self.box((20, 570, 705, 120))
        for j, line in enumerate(self.log):
            self.text(line, (36, 584 + j * 32), self.f, "text" if j == len(self.log) - 1 else "mute")
        # верхняя плашка состояния
        pygame.draw.rect(self.screen, TINT[s.get("color", "blue")], (20, 16, 1080, 60), 0, 12)
        pygame.draw.rect(self.screen, COL[s.get("color", "blue")], (20, 16, 1080, 60), 3, 12)
        self.text(s["text"], (44, 46), self.f_big, "text", "midleft")
        self.text(f"×{self.speed:g}" + ("  пауза" if self.paused else ""), (1084, 46), self.f, "mute", "midright")
        self.text("ПРОБЕЛ — пауза   ↑/↓ — скорость   R — заново   ESC — выход", (1100, 680), self.f_small, "mute", "bottomright")

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif e.key == pygame.K_UP:
                        self.speed = min(16, self.speed * 2)
                    elif e.key == pygame.K_DOWN:
                        self.speed = max(0.25, self.speed / 2)
                    elif e.key == pygame.K_r:
                        self.reset()
                        self.paused = False
            self.update(clock.tick(60) / 1000)
            self.draw()
            pygame.display.flip()


if __name__ == "__main__":
    App().run()
