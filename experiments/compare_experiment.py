"""과제: 개별 체이닝과 선형 탐지의 탐색 비용 비교.

같은 키를 같은 크기(M = 4093, 늘리지 않음)의 두 테이블에 넣고 적재율 α = 0.1 ~ 0.9에서
  - 성공 탐색: 넣은 키를 모두 찾을 때의 평균 비용
  - 실패 탐색: 넣지 않은 키 4093개를 찾을 때의 평균 비용
을 잰다. 비용은 체이닝은 비교한 노드 수, 선형 탐지는 들여다본 칸 수다.
시드를 바꿔 TRIALS번 되풀이한 평균을 이론값과 함께 표와 그래프로 보인다.

    make compare   ->  experiments/compare.csv, experiments/compare.svg
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from hash_table import HashTable  # noqa: E402
from probing_table import ProbingTable  # noqa: E402
from probe_experiment import average_cost, random_urls  # noqa: E402
import svgplot  # noqa: E402

M = 4093
LOADS = [round(0.1 + 0.05 * i, 2) for i in range(17)]  # 0.1, 0.15, ..., 0.9
MISS_QUERIES = M
TRIALS = 10


def chain_hit(a):
    return 1 + a / 2


def chain_miss(a):
    return a


def probe_hit(a):
    return (1 + 1 / (1 - a)) / 2


def probe_miss(a):
    return (1 + 1 / (1 - a) ** 2) / 2


def run_trial(seed):
    rng = random.Random(1000 + seed)
    n_max = round(LOADS[-1] * M)
    keys = random_urls(n_max + MISS_QUERIES, rng)
    inserted, misses = keys[:n_max], keys[n_max:]
    chain = HashTable(capacity=M, max_load=None)
    probe = ProbingTable(capacity=M, max_load=None)
    rows = []
    done = 0
    for alpha in LOADS:
        n = round(alpha * M)
        while done < n:  # 같은 키를 같은 순서로 두 테이블에 넣는다
            chain.put(inserted[done], done)
            probe.put(inserted[done], done)
            done += 1
        assert chain.capacity == probe.capacity == M and len(chain) == len(probe) == n
        rows.append((n / M, n,
                     average_cost(chain, inserted[:n]), average_cost(chain, misses),
                     average_cost(probe, inserted[:n]), average_cost(probe, misses)))
    return rows


def main():
    trials = [run_trial(seed) for seed in range(TRIALS)]
    results = []
    for i in range(len(LOADS)):
        a, n = trials[0][i][0], trials[0][i][1]
        avg = [sum(t[i][j] for t in trials) / TRIALS for j in range(2, 6)]
        results.append((a, n, avg[0], chain_hit(a), avg[1], chain_miss(a), avg[2], probe_hit(a), avg[3], probe_miss(a)))

    csv_path = os.path.join(HERE, "compare.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("load_factor,keys,capacity,chain_hit,chain_hit_theory,chain_miss,chain_miss_theory,"
                "probe_hit,probe_hit_theory,probe_miss,probe_miss_theory\n")
        for r in results:
            f.write("%.4f,%d,%d,%s\n" % (r[0], r[1], M, ",".join("%.4f" % v for v in r[2:])))

    print("같은 키, 같은 크기 M = %d, 시드 %d개 평균, 실패 탐색 키 %d개" % (M, TRIALS, MISS_QUERIES))
    print("체이닝 = 비교한 노드 수, 선형 탐지 = 들여다본 칸 수 (괄호 안은 이론값)")
    print("%5s %5s | %16s %16s | %16s %18s" % ("α", "n", "체이닝 성공", "체이닝 실패", "선형탐지 성공", "선형탐지 실패"))
    for a, n, ch, cht, cm, cmt, ph, pht, pm, pmt in results:
        print("%5.2f %5d | %7.3f (%6.3f) %7.3f (%6.3f) | %7.3f (%6.3f) %8.3f (%7.3f)"
              % (a, n, ch, cht, cm, cmt, ph, pht, pm, pmt))

    xs = [r[0] for r in results]
    fine = [i / 100 for i in range(5, 91)]  # 이론 곡선은 촘촘하게
    blue, orange = "#2563eb", "#ea580c"
    hit_series = [
        ("체이닝 실측 (비교 노드)", xs, [r[2] for r in results], blue, False, True),
        ("체이닝 이론 1 + α/2", fine, [chain_hit(a) for a in fine], blue, True, False),
        ("선형 탐지 실측 (들여다본 칸)", xs, [r[6] for r in results], orange, False, True),
        ("선형 탐지 이론 (1 + 1/(1-α))/2", fine, [probe_hit(a) for a in fine], orange, True, False),
    ]
    miss_series = [
        ("체이닝 실측", xs, [r[4] for r in results], blue, False, True),
        ("체이닝 이론 α", fine, [chain_miss(a) for a in fine], blue, True, False),
        ("선형 탐지 실측", xs, [r[8] for r in results], orange, False, True),
        ("선형 탐지 이론 (1 + 1/(1-α)²)/2", fine, [probe_miss(a) for a in fine], orange, True, False),
    ]
    xt = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    ymax_miss = max(max(r[8] for r in results), probe_miss(0.9)) * 1.08
    parts = []
    parts += svgplot.panel(0, 0, 480, 380, "성공 탐색의 평균 비용", "적재율 α", "평균 비용", hit_series,
                           (0.05, 0.95), (0, 6), xticks=xt)
    parts += svgplot.panel(480, 0, 480, 380, "실패 탐색의 평균 비용", "적재율 α", "평균 비용", miss_series,
                           (0.05, 0.95), (0, ymax_miss), xticks=xt)
    parts.append("<text x='58' y='402' font-size='12' fill='#4b5563' %s>같은 키를 M = %d칸 두 테이블에 넣음 · 시드 %d개 평균 · "
                 "실선+점 = 실측, 점선 = 이론</text>" % (svgplot.FONT, M, TRIALS))
    legend_series = [
        ("개별 체이닝 실측 (비교한 노드 수)", [], [], blue, False, True),
        ("선형 탐지 실측 (들여다본 칸 수)", [], [], orange, False, True),
        ("개별 체이닝 이론: 성공 1 + α/2, 실패 α", [], [], blue, True, False),
        ("선형 탐지 이론: 성공 (1 + 1/(1-α))/2, 실패 (1 + 1/(1-α)²)/2", [], [], orange, True, False),
    ]
    parts += svgplot.legend(70, 428, legend_series, columns=2, col_width=330)
    svg_path = os.path.join(HERE, "compare.svg")
    svgplot.save(svg_path, 960, 480, parts)
    print("저장: %s, %s" % (os.path.relpath(csv_path), os.path.relpath(svg_path)))


if __name__ == "__main__":
    main()
