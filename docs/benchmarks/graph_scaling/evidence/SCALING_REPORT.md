# TS-Core Scaling Report

TS-Benchmarks is not a victory-lap repo. It is a falsification harness. The first result shows clean relaxation on some graph families and failure on scale-free graphs, which is now the next target.

This report is generated from local benchmark receipts. It is not a capability claim and not a transformer comparison.

## What Worked

- `random`: relaxed cleanly with nonzero localization up to 10000 nodes.
- `small_world`: relaxed cleanly with nonzero localization up to 10000 nodes.

## What Failed

- `scale-scale_free-10000-seed42`: final tension 0.303546, contradiction-localization F1 0.000.
- `scale-scale_free-1000-seed42`: final tension 0.257588, contradiction-localization F1 0.000.
- `scale-scale_free-100-seed42`: final tension 0.210391, contradiction-localization F1 0.000.

## What This Means

- The reference relaxation path can reduce injected tension on some sparse synthetic graph families.
- The same reference config is not yet robust to scale-free hub structure.
- Scale-free failure is a useful target because real knowledge graphs often have hub-heavy structure.
- These results justify diagnostics and kernel work; they do not justify broad capability claims.

## Next Experiment

- Add hub-aware relaxation controls: degree-normalized updates, hub clipping, and per-context hub splitting.
- Re-run the same 100/1k/10k scale-free sweep before changing the claim boundary.
- Add NetworkX, belief-propagation, and Bayesian provenance baselines.

## Summary Metrics

| Run | Graph | Nodes | Edges | Runtime s | Peak MB | Final tension | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| scale-random-10000-seed42 | random | 10000 | 30010 | 19.5207 | 4.59 | 0.000191 | 0.600 |
| scale-random-1000-seed42 | random | 1000 | 3003 | 1.7934 | 0.36 | 0.000206 | 0.833 |
| scale-random-100-seed42 | random | 100 | 301 | 0.1501 | 0.04 | 0.000219 | 0.500 |
| scale-scale_free-10000-seed42 | scale_free | 10000 | 30004 | 22.5916 | 4.58 | 0.303546 | 0.000 |
| scale-scale_free-1000-seed42 | scale_free | 1000 | 2997 | 2.1360 | 0.36 | 0.257588 | 0.000 |
| scale-scale_free-100-seed42 | scale_free | 100 | 295 | 0.1912 | 0.04 | 0.210391 | 0.000 |
| scale-small_world-10000-seed42 | small_world | 10000 | 30008 | 21.2140 | 4.59 | 0.001033 | 0.600 |
| scale-small_world-1000-seed42 | small_world | 1000 | 3002 | 2.0684 | 0.36 | 0.000956 | 0.667 |
| scale-small_world-100-seed42 | small_world | 100 | 301 | 0.1838 | 0.04 | 0.000769 | 1.000 |

## Baseline Comparison

| Run | TS F1 | Degree F1 | PageRank-like F1 | Random residual F1 | TS vs best baseline |
| --- | ---: | ---: | ---: | ---: | --- |
| scale-random-10000-seed42 | 0.600 | 0.000 | 1.000 | 0.050 | loses to pagerank_like by 0.400 |
| scale-random-1000-seed42 | 0.833 | 0.000 | 1.000 | 0.000 | loses to pagerank_like by 0.167 |
| scale-random-100-seed42 | 0.500 | 0.000 | 1.000 | 0.000 | loses to pagerank_like by 0.500 |
| scale-scale_free-10000-seed42 | 0.000 | 0.000 | 1.000 | 0.050 | loses to pagerank_like by 1.000 |
| scale-scale_free-1000-seed42 | 0.000 | 0.000 | 1.000 | 0.000 | loses to pagerank_like by 1.000 |
| scale-scale_free-100-seed42 | 0.000 | 0.000 | 1.000 | 0.000 | loses to pagerank_like by 1.000 |
| scale-small_world-10000-seed42 | 0.600 | 0.350 | 1.000 | 0.000 | loses to pagerank_like by 0.400 |
| scale-small_world-1000-seed42 | 0.667 | 0.500 | 1.000 | 0.000 | loses to pagerank_like by 0.333 |
| scale-small_world-100-seed42 | 1.000 | 0.000 | 1.000 | 0.000 | equivalent to pagerank_like |

## Scale-Free Failure Diagnostics

### scale-scale_free-10000-seed42

- Plateau step: 33
- Hub residual tension share: 0.913 at degree threshold 15
- Confusion matrix: TP=0 FP=20 FN=20 TN=9960
- Active frontier first/last: [10000, 10000, 10000, 10000, 10000] -> [10000, 10000, 10000, 10000, 10000]

| Degree bucket | Nodes | Total tension | Avg tension | Max tension |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0 | 0.000000 | 0.000000 | 0.000000 |
| 1-2 | 0 | 0.000000 | 0.000000 | 0.000000 |
| 3-5 | 7156 | 2638.628673 | 0.368730 | 1.657856 |
| 6-10 | 1915 | 1252.519198 | 0.654057 | 2.541024 |
| 11-25 | 740 | 1489.858835 | 2.013323 | 11.502521 |
| 26-50 | 141 | 1996.951790 | 14.162779 | 22.396830 |
| 51+ | 48 | 1729.621157 | 36.033774 | 86.395115 |

| Edge | Relation | Tension | Src degree | Dst degree | Provenance |
| ---: | --- | ---: | ---: | ---: | --- |
| 29994 | contradicts | 2.462241 | 8 | 32 | synthetic_injected_contradiction |
| 362 | support | 1.995744 | 23 | 61 | synthetic |
| 439 | support | 1.995738 | 45 | 105 | synthetic |
| 727 | support | 1.995535 | 30 | 25 | synthetic |
| 632 | support | 1.994918 | 27 | 24 | synthetic |
| 134 | support | 1.992319 | 108 | 78 | synthetic |
| 1076 | support | 1.984312 | 28 | 38 | synthetic |
| 457 | support | 1.983403 | 26 | 113 | synthetic |
| 1292 | support | 1.982346 | 24 | 42 | synthetic |
| 1 | support | 1.981056 | 222 | 168 | synthetic |
### scale-scale_free-1000-seed42

- Plateau step: 30
- Hub residual tension share: 0.908 at degree threshold 15
- Confusion matrix: TP=0 FP=6 FN=6 TN=988
- Active frontier first/last: [1000, 1000, 1000, 1000, 1000] -> [1000, 1000, 1000, 1000, 1000]

| Degree bucket | Nodes | Total tension | Avg tension | Max tension |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0 | 0.000000 | 0.000000 | 0.000000 |
| 1-2 | 0 | 0.000000 | 0.000000 | 0.000000 |
| 3-5 | 711 | 222.879391 | 0.313473 | 1.629041 |
| 6-10 | 190 | 107.184538 | 0.564129 | 1.806120 |
| 11-25 | 84 | 141.971952 | 1.690142 | 10.185689 |
| 26-50 | 10 | 156.607420 | 15.660742 | 20.713563 |
| 51+ | 5 | 143.346864 | 28.669373 | 47.971883 |

| Edge | Relation | Tension | Src degree | Dst degree | Provenance |
| ---: | --- | ---: | ---: | ---: | --- |
| 3 | support | 1.971093 | 53 | 57 | synthetic |
| 75 | support | 1.883342 | 24 | 116 | synthetic |
| 13 | support | 1.866448 | 66 | 59 | synthetic |
| 7 | support | 1.765157 | 47 | 116 | synthetic |
| 62 | support | 1.642699 | 34 | 66 | synthetic |
| 10 | support | 1.595982 | 31 | 59 | synthetic |
| 15 | support | 1.588853 | 50 | 57 | synthetic |
| 124 | support | 1.563735 | 27 | 31 | synthetic |
| 227 | support | 1.515376 | 24 | 47 | synthetic |
| 94 | support | 1.500262 | 47 | 116 | synthetic |
### scale-scale_free-100-seed42

- Plateau step: 64
- Hub residual tension share: 0.917 at degree threshold 14
- Confusion matrix: TP=0 FP=2 FN=2 TN=96
- Active frontier first/last: [100, 100, 100, 100, 100] -> [100, 100, 100, 100, 100]

| Degree bucket | Nodes | Total tension | Avg tension | Max tension |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0 | 0.000000 | 0.000000 | 0.000000 |
| 1-2 | 0 | 0.000000 | 0.000000 | 0.000000 |
| 3-5 | 66 | 17.589638 | 0.266510 | 0.984947 |
| 6-10 | 22 | 8.462086 | 0.384640 | 1.227588 |
| 11-25 | 10 | 14.570838 | 1.457084 | 4.067827 |
| 26-50 | 2 | 21.442745 | 10.721372 | 10.992310 |
| 51+ | 0 | 0.000000 | 0.000000 | 0.000000 |

| Edge | Relation | Tension | Src degree | Dst degree | Provenance |
| ---: | --- | ---: | ---: | ---: | --- |
| 6 | support | 1.320658 | 20 | 28 | synthetic |
| 8 | support | 1.157161 | 20 | 27 | synthetic |
| 172 | support | 1.067776 | 8 | 27 | synthetic |
| 5 | support | 1.061136 | 27 | 16 | synthetic |
| 145 | support | 1.057699 | 4 | 27 | synthetic |
| 150 | support | 1.037356 | 4 | 28 | synthetic |
| 288 | support | 1.017616 | 3 | 27 | synthetic |
| 3 | support | 1.014154 | 27 | 23 | synthetic |
| 76 | support | 0.987433 | 8 | 27 | synthetic |
| 126 | support | 0.981071 | 3 | 28 | synthetic |
