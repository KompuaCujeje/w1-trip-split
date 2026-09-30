"""Кто кому должен: балансы и план переводов по data.json.

Логика — как в build.py этапа 1 (точные дроби, жадный план переводов).
Правка этапа 2 одна: курс ищется по валюте и дате (поле `rates`),
возврат пересчитывается по курсу своей даты, а если курса нет — ошибка
(раньше любая не-рублёвая сумма молча умножалась на единственный курс).
Старый формат `rate: {"GEL_RUB": x}` по-прежнему работает.

Запуск: python stage2/split.py stage2/beijing.json
"""

import json
import sys
from fractions import Fraction as F


def load_rates(d):
    if "rates" in d:
        return {(x["currency"], x["date"]): F(str(x["rub_per_unit"])) for x in d["rates"]}
    # формат этапа 1: один курс на всю поездку
    return {(k.split("_")[0], None): F(str(v)) for k, v in d["rate"].items() if k.endswith("_RUB")}


def run(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    people = d["people"]
    rates = load_rates(d)

    def rub(cur, amount, date):
        if cur == "RUB":
            return F(str(amount))
        key = (cur, date) if (cur, date) in rates else (cur, None)
        if key not in rates:
            raise SystemExit(f"нет курса {cur} на {date}")
        return F(str(amount)) * rates[key]

    paid = {p: F(0) for p in people}
    share = {p: F(0) for p in people}
    for r in d["receipts"]:
        x = rub(r["currency"], r["amount"], r["date"])
        paid[r["payer"]] += x
        for q in r["split"]:
            share[q] += x / len(r["split"])
    for v in d["refunds"]:
        x = rub(v["currency"], v["amount"], v["date"])  # возврат — по курсу даты возврата
        paid[v["to"]] -= x
        for q in v["split"]:
            share[q] -= x / len(v["split"])
    bal = {p: paid[p] - share[p] for p in people}

    # план: крупнейший должник платит крупнейшему кредитору
    b = dict(bal)
    plan = []
    while True:
        deb = min(people, key=lambda p: (b[p], people.index(p)))
        cr = max(people, key=lambda p: (b[p], -people.index(p)))
        if b[deb] == 0 and b[cr] == 0:
            break
        t = min(-b[deb], b[cr])
        plan.append((deb, cr, t))
        b[deb] += t
        b[cr] -= t
    return paid, share, bal, plan


def fmt(x, sign=False):
    s = f"{float(x):{'+' if sign else ''},.2f}"
    return s.replace(",", " ").replace(".", ",")


if __name__ == "__main__":
    paid, share, bal, plan = run(sys.argv[1])
    for p in bal:
        print(f"{p}: заплатил {fmt(paid[p])} · доля {fmt(share[p])} · баланс {fmt(bal[p], True)} ₽")
    print("сумма балансов:", fmt(sum(bal.values())))
    for a, c, t in plan:
        print(f"{a} → {c}: {fmt(t)} ₽")
