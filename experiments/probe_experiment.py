"""6단계: 개별 체이닝의 적재율에 따른 탐색 비용.

칸 수 M = 4093으로 고정하고 늘리지 않는다 (HashTable(capacity=4093, max_load=None)).
무작위 URL을 넣어 가며 적재율 α = 0.25 ~ 4에서
  - 성공 탐색: 넣은 키를 모두 찾을 때 비교한 노드 수의 평균
  - 실패 탐색: 넣지 않은 키 4093개를 찾을 때 비교한 노드 수의 평균
을 재고, 이론값(성공 약 1 + α/2, 실패 약 α)과 비교한다.
시드를 바꿔 TRIALS번 되풀이한 평균을 쓴다.

    make experiment   ->  experiments/results.csv, experiments/probes.svg
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from hash_table import HashTable  # noqa: E402
import svgplot  # noqa: E402

M = 4093
LOADS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
MISS_QUERIES = M
TRIALS = 5
PATH_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
HOSTS = ["example.com", "news.example.org", "blog.example.net", "shop.example.co.kr", "yonsei.ac.kr"]


def random_urls(count, rng):
    """서로 다른 무작위 URL count개. 중복 확인에도 직접 만든 해시 테이블을 쓴다."""
    seen = HashTable()
    urls = []
    while len(urls) < count:
        path = "".join(rng.choice(PATH_CHARS) for _ in range(rng.randint(6, 24)))
        u = "https://%s/%s" % (rng.choice(HOSTS), path)
        if u not in seen:
            seen.put(u, True)
            urls.append(u)
    return urls


def average_cost(table, keys):
    total = 0
    for k in keys:
        total += table.find(k)[2]
    return total / len(keys)


def run_trial(seed):
    rng = random.Random(seed)
    n_max = round(LOADS[-1] * M)
    keys = random_urls(n_max + MISS_QUERIES, rng)
    inserted, misses = keys[:n_max], keys[n_max:]
    table = HashTable(capacity=M, max_load=None)
    rows = []
    done = 0
    for alpha in LOADS:
        n = round(alpha * M)
        while done < n:
            table.put(inserted[done], done)
            done += 1
        assert table.capacity == M and len(table) == n
        hit = average_cost(table, inserted[:n])
        miss = average_cost(table, misses)
        rows.append((alpha, n, table.load_factor(), hit, miss))
    return rows


def main():
    trials = [run_trial(seed) for seed in range(TRIALS)]
    results = []
    for i, alpha in enumerate(LOADS):
        n = trials[0][i][1]
        real_alpha = trials[0][i][2]
        hit = sum(t[i][3] for t in trials) / TRIALS
        miss = sum(t[i][4] for t in trials) / TRIALS
        results.append((alpha, n, real_alpha, hit, 1 + real_alpha / 2, miss, real_alpha))

    csv_path = os.path.join(HERE, "results.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("load_factor,keys,capacity,hit_measured,hit_theory,miss_measured,miss_theory\n")
        for alpha, n, real_alpha, hit, hit_t, miss, miss_t in results:
            f.write("%.4f,%d,%d,%.4f,%.4f,%.4f,%.4f\n" % (real_alpha, n, M, hit, hit_t, miss, miss_t))

    print("개별 체이닝, 칸 수 M = %d, 시드 %d개 평균, 실패 탐색 키 %d개" % (M, TRIALS, MISS_QUERIES))
    print("%6s %6s | %8s %8s %7s | %8s %8s %7s" % ("α", "키 수", "성공 실측", "이론", "차이", "실패 실측", "이론", "차이"))
    for alpha, n, real_alpha, hit, hit_t, miss, miss_t in results:
        print("%6.2f %6d | %8.3f %8.3f %+7.3f | %8.3f %8.3f %+7.3f"
              % (real_alpha, n, hit, hit_t, hit - hit_t, miss, miss_t, miss - miss_t))

    xs = [r[2] for r in results]
    blue, orange = "#2563eb", "#ea580c"
    series = [
        ("성공 탐색 (실측)", xs, [r[3] for r in results], blue, False, True),
        ("성공 탐색 이론 1 + α/2", xs, [r[4] for r in results], blue, True, False),
        ("실패 탐색 (실측)", xs, [r[5] for r in results], orange, False, True),
        ("실패 탐색 이론 α", xs, [r[6] for r in results], orange, True, False),
    ]
    parts = svgplot.panel(0, 0, 640, 400, "개별 체이닝: 적재율에 따른 평균 비교 노드 수 (M = %d)" % M,
                          "적재율 α = 키 수 / 칸 수", "평균 비교 노드 수", series,
                          (0, 4.2), (0, 4.5), xticks=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4])
    parts += svgplot.legend(80, 420, series, columns=2, col_width=260)
    svg_path = os.path.join(HERE, "probes.svg")
    svgplot.save(svg_path, 640, 470, parts)
    print("저장: %s, %s" % (os.path.relpath(csv_path), os.path.relpath(svg_path)))


if __name__ == "__main__":
    main()
