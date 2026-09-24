# Volume Impact Analysis: `T` / `15min`

## Data and Methodology
- Source: read-only SQLite database `/tmp/tech_news_trader_analysis.db`.
- Candles analyzed: **38144**, from **2024-09-24 09:45:00** to **2026-09-24 12:00:00**.
- Volume spike: `volume >= SMA(20) * 2.5` **OR** `volume Z-score(50) > 2.5`.
- ATR: prior `14` true ranges; forward horizon: next `4` candles (15-60 minutes).
- Rolling baselines exclude the signal candle to avoid look-ahead contamination.
- Impulse requires a break of the signal high/low and movement greater than 1 ATR from the signal close.
- Reversal requires a close across the signal open, covering the signal body. If an impulse is later reversed, it is a false breakout and belongs to the reversal group.
- MFE/MAE are measured from the signal close over the available forward bars; MAE is reported as a positive adverse percentage.
- Mean 15m/30m/60m changes are raw close-to-close percentages, not direction-normalized returns; small candle-type samples should not be overinterpreted.
- Adjacent signal candles are retained as separate events; no de-clustering or trade-level de-duplication is applied.

## Statistical Summary
- Всего событий: **3896**.
- С полным горизонтом 60 минут: **3895**; событий у конца выборки: **1**.
- Продолжение с истинным пробоем: **35.9%**.
- Флет/затухание без подтвержденного импульса: **31.8%**.
- Разворот, включая ложный пробой: **32.3%**.
- Среднее изменение цены: 15m **0.010%**, 30m **0.018%**, 60m **0.026%**.
- Наибольшая доля продолжения среди типов: **Doji** (79.2%, n=24).
- Наибольшая доля разворотов среди типов: **Bearish pin-bar / upper rejection** (50.4%, n=782).
- Максимальное среднее необусловленное изменение за 60m: **Doji** (0.126%, n=24).

| Candle Type | Events | Mean 15m | Mean 30m | Mean 60m | Continuation | Flat | Reversal |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bearish pin-bar / upper rejection | 782 | 0.024% | 0.026% | 0.022% | 25.4% | 24.2% | 50.4% |
| Bullish pin-bar / lower rejection | 843 | -0.016% | -0.000% | 0.015% | 22.9% | 28.2% | 48.9% |
| Doji | 24 | 0.079% | 0.129% | 0.126% | 79.2% | 20.8% | 0.0% |
| Doji / lower rejection | 18 | 0.010% | -0.018% | 0.042% | 61.1% | 38.9% | 0.0% |
| Doji / upper rejection | 15 | -0.020% | -0.039% | 0.086% | 73.3% | 26.7% | 0.0% |
| Full-bodied bearish | 774 | 0.019% | 0.015% | 0.019% | 46.3% | 35.5% | 18.2% |
| Full-bodied bullish | 826 | 0.030% | 0.050% | 0.065% | 46.0% | 39.1% | 14.9% |
| Small-body bearish | 293 | -0.034% | -0.051% | -0.066% | 40.6% | 30.0% | 29.4% |
| Small-body bullish | 320 | 0.002% | 0.034% | 0.052% | 34.4% | 33.8% | 31.9% |

## Interpretation
- Directional volume is most useful when the candle has a large body, a high range/ATR ratio, and the first subsequent bars break the signal extreme without closing back through its body.
- Long upper shadows indicate supply/rejection risk; long lower shadows indicate demand/rejection risk. A high volume ratio alone is not treated as directional evidence.
- A false breakout is separated from a clean continuation because the initial excursion beyond the range is subsequently rejected within the four-bar observation window.

## Detected Events
| Timestamp | Volume Ratio | Candle Type | Reaction (Next 1-4 bars) | Net Change % (15m / 30m / 60m) | Outcome Status | Body/Range | Upper wick | Lower wick | Range/ATR | MFE / MAE |
|---|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 2024-09-24 18:15 | 5.38x | Small-body bullish | Flat / fading | 0.057% / 0.057% / 0.114% | Position building in range | 56.7% | 26.7% | 16.7% | 5.71x | 0.171% / 0.038% |
| 2024-09-25 10:00 | 10.06x | Bullish pin-bar / lower rejection | Reversal | 0.323% / 0.133% / 0.057% | Liquidity sweep / reversal | 29.5% | 9.1% | 61.4% | 6.16x | 0.323% / 0.323% |
| 2024-09-25 10:15 | 4.38x | Bullish pin-bar / lower rejection | Reversal | -0.189% / -0.360% / -0.019% | Liquidity sweep / reversal | 52.9% | 0.0% | 47.1% | 3.58x | 0.000% / 0.511% |
| 2024-09-25 11:00 | 2.72x | Small-body bullish | Impulse / continuation | 0.247% / 0.646% / 2.640% | True breakout | 30.0% | 35.0% | 35.0% | 1.56x | 2.697% / -0.019% |
| 2024-09-25 11:30 | 3.23x | Full-bodied bullish | Impulse / continuation | 0.830% / 1.981% / 4.019% | True breakout | 91.7% | 0.0% | 8.3% | 1.62x | 4.283% / 0.094% |
| 2024-09-25 11:45 | 4.21x | Full-bodied bullish | Impulse / continuation | 1.141% / 2.002% / 2.919% | True breakout | 86.8% | 7.5% | 5.7% | 3.48x | 4.004% / 0.206% |
| 2024-09-25 12:00 | 6.39x | Full-bodied bullish | Impulse / continuation | 0.851% / 1.998% / 1.739% | True breakout | 78.7% | 4.0% | 17.3% | 4.05x | 2.831% / 0.056% |
| 2024-09-25 12:15 | 9.14x | Bearish pin-bar / upper rejection | Impulse / continuation | 1.137% / 0.899% / 0.660% | True breakout | 47.9% | 49.0% | 3.1% | 4.07x | 1.963% / 0.000% |
| 2024-09-25 12:30 | 5.31x | Full-bodied bullish | Impulse / continuation | -0.236% / -0.254% / -0.599% | True breakout | 81.6% | 18.4% | 0.0% | 2.52x | 0.816% / 0.907% |
| 2024-09-25 12:45 | 3.56x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.018% / -0.236% / -1.091% | True breakout | 20.6% | 64.7% | 14.7% | 1.95x | 1.182% / 0.200% |
| 2024-09-26 10:00 | 6.05x | Small-body bullish | Impulse / continuation | 0.263% / -0.075% / 0.997% | True breakout | 20.9% | 39.5% | 39.5% | 4.04x | 1.091% / 0.734% |
| 2024-09-26 10:15 | 3.21x | Bullish pin-bar / lower rejection | Reversal | -0.338% / -0.582% / 0.507% | Liquidity sweep / reversal | 28.3% | 0.0% | 71.7% | 2.04x | 1.164% / 0.713% |
| 2024-09-26 11:00 | 3.93x | Full-bodied bullish | Flat / fading | -0.224% / -0.503% / -0.056% | Weak move without breakout | 86.4% | 6.2% | 7.4% | 3.06x | 0.429% / 0.764% |
| 2024-09-26 11:15 | 3.57x | Bullish pin-bar / lower rejection | Flat / fading | -0.280% / -0.075% / -0.075% | Position building in range | 18.8% | 35.9% | 45.3% | 2.03x | 0.486% / 0.280% |
| 2024-09-26 16:15 | 3.42x | Full-bodied bearish | Flat / fading | 0.057% / 0.019% / 0.000% | Position building in range | 60.0% | 7.4% | 32.6% | 4.46x | 0.516% / 0.401% |
| 2024-09-27 10:00 | 14.23x | Full-bodied bullish | Flat / fading | -0.380% / -0.361% / -0.209% | Weak move without breakout | 60.0% | 31.1% | 8.9% | 5.83x | 0.171% / 0.722% |
| 2024-09-27 10:15 | 4.42x | Full-bodied bearish | Impulse / continuation | 0.019% / 0.210% / 0.248% | True breakout | 76.9% | 0.0% | 23.1% | 2.56x | 0.343% / 0.553% |
| 2024-09-27 10:30 | 3.69x | Doji / lower rejection | Impulse / continuation | 0.191% / 0.153% / 0.572% | True breakout | 0.0% | 32.1% | 67.9% | 2.61x | 0.572% / 0.572% |
| 2024-09-27 10:45 | 3.04x | Small-body bullish | Impulse / continuation | -0.038% / 0.038% / 0.647% | True breakout | 45.8% | 37.5% | 16.7% | 2.00x | 0.876% / 0.152% |
| 2024-09-27 11:00 | 2.76x | Bearish pin-bar / upper rejection | Reversal | 0.076% / 0.419% / 0.819% | Liquidity sweep / reversal | 11.5% | 65.4% | 23.1% | 1.96x | 0.019% / 1.181% |
| 2024-09-27 11:45 | 4.84x | Small-body bullish | Flat / fading | 0.132% / -0.114% / 0.303% | Weak move without breakout | 41.2% | 35.3% | 23.5% | 2.15x | 0.492% / 0.227% |
| 2024-09-27 12:00 | 2.76x | Bearish pin-bar / upper rejection | Reversal | -0.246% / -0.076% / -0.057% | Liquidity sweep / reversal | 21.4% | 67.9% | 10.7% | 1.57x | 0.265% / 0.359% |
| 2024-09-30 10:00 | 24.43x | Full-bodied bullish | Impulse / continuation | 0.000% / -0.112% / -0.075% | True breakout | 73.2% | 3.6% | 23.2% | 6.88x | 0.318% / 0.579% |
| 2024-09-30 10:15 | 6.56x | Doji / lower rejection | Flat / fading | -0.112% / -0.318% / -0.056% | Weak move without breakout | 0.0% | 36.8% | 63.2% | 3.37x | 0.579% / 0.579% |
| 2024-09-30 10:30 | 5.71x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.206% / 0.037% / 0.056% | True breakout | 18.5% | 66.7% | 14.8% | 2.02x | 0.467% / 0.299% |
| 2024-09-30 11:00 | 3.64x | Bullish pin-bar / lower rejection | Flat / fading | 0.019% / 0.019% / -0.187% | Weak move without breakout | 32.4% | 27.0% | 40.5% | 2.28x | 0.262% / 0.299% |
| 2024-09-30 22:45 | 2.65x | Small-body bearish | Flat / fading | 0.057% / -0.133% / -0.038% | Position building in range | 58.3% | 5.6% | 36.1% | 4.58x | 0.152% / 0.152% |
| 2024-10-01 10:00 | 13.16x | Full-bodied bearish | Impulse / continuation | 0.172% / 0.019% / -0.535% | True breakout | 82.1% | 3.6% | 14.3% | 2.38x | 0.593% / 0.382% |
| 2024-10-01 10:15 | 7.18x | Bullish pin-bar / lower rejection | Reversal | -0.153% / -0.668% / -0.649% | Liquidity sweep / reversal | 34.8% | 17.4% | 47.8% | 1.71x | 0.210% / 0.763% |
| 2024-10-01 10:45 | 4.25x | Full-bodied bearish | Impulse / continuation | -0.038% / 0.019% / -0.692% | True breakout | 71.1% | 23.7% | 5.3% | 2.42x | 0.999% / 0.269% |
| 2024-10-01 11:00 | 3.01x | Bearish pin-bar / upper rejection | Reversal | 0.058% / 0.096% / -0.826% | Liquidity sweep / reversal | 15.4% | 61.5% | 23.1% | 0.73x | 1.038% / 0.307% |
| 2024-10-01 11:45 | 4.31x | Full-bodied bearish | Flat / fading | -0.174% / 0.039% / 0.039% | Weak move without breakout | 70.9% | 0.0% | 29.1% | 3.04x | 0.387% / 0.155% |
| 2024-10-01 14:00 | 2.82x | Full-bodied bearish | Flat / fading | -0.273% / -0.137% / -0.215% | Weak move without breakout | 74.5% | 5.5% | 20.0% | 2.79x | 0.488% / 0.117% |
| 2024-10-02 10:00 | 8.76x | Full-bodied bullish | Flat / fading | -0.019% / 0.097% / -0.155% | Weak move without breakout | 74.5% | 18.2% | 7.3% | 6.02x | 0.271% / 0.271% |
| 2024-10-02 10:15 | 4.90x | Bearish pin-bar / upper rejection | Reversal | 0.116% / 0.077% / -0.232% | Liquidity sweep / reversal | 7.1% | 46.4% | 46.4% | 2.19x | 0.348% / 0.232% |
| 2024-10-02 10:30 | 3.74x | Bullish pin-bar / lower rejection | Reversal | -0.039% / -0.251% / -0.503% | Liquidity sweep / reversal | 28.0% | 24.0% | 48.0% | 1.77x | 0.097% / 0.522% |
| 2024-10-02 15:30 | 5.29x | Full-bodied bearish | Impulse / continuation | -0.672% / 0.178% / 0.198% | True breakout | 81.8% | 1.8% | 16.4% | 3.99x | 1.126% / 0.415% |
| 2024-10-02 15:45 | 5.97x | Full-bodied bearish | Reversal | 0.855% / 0.437% / 0.954% | Liquidity sweep / reversal | 81.4% | 4.7% | 14.0% | 2.69x | 0.457% / 1.153% |
| 2024-10-02 16:00 | 5.90x | Small-body bullish | Flat / fading | -0.414% / 0.020% / -0.237% | Weak move without breakout | 60.0% | 5.7% | 34.3% | 3.95x | 0.296% / 0.513% |
| 2024-10-03 10:00 | 8.03x | Small-body bullish | Reversal | -0.716% / -0.617% / -0.040% | Liquidity sweep / reversal | 46.9% | 22.4% | 30.6% | 5.24x | 0.577% / 1.054% |
| 2024-10-03 10:15 | 4.72x | Full-bodied bearish | Reversal | 0.100% / 0.441% / 1.042% | Liquidity sweep / reversal | 63.2% | 7.0% | 29.8% | 4.67x | 0.240% / 1.302% |
| 2024-10-03 10:30 | 3.32x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.340% / 0.580% / 1.281% | True breakout | 12.5% | 46.9% | 40.6% | 2.21x | 1.421% / 0.200% |
| 2024-10-03 10:45 | 3.43x | Small-body bullish | Impulse / continuation | 0.239% / 0.598% / 0.678% | True breakout | 40.5% | 35.7% | 23.8% | 2.63x | 1.077% / 0.100% |
| 2024-10-03 11:00 | 4.25x | Bearish pin-bar / upper rejection | Flat / fading | 0.358% / 0.696% / 0.179% | Weak move without breakout | 22.9% | 64.6% | 12.5% | 2.61x | 0.836% / 0.179% |
| 2024-10-03 15:15 | 2.57x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.984% / 1.279% / 1.220% | True breakout | 5.9% | 64.7% | 29.4% | 1.85x | 1.653% / 0.059% |
| 2024-10-04 10:00 | 15.72x | Bearish pin-bar / upper rejection | Reversal | 0.233% / 1.067% / 0.892% | Liquidity sweep / reversal | 45.1% | 54.9% | 0.0% | 9.04x | 0.175% / 1.300% |
| 2024-10-04 10:15 | 4.32x | Small-body bullish | Impulse / continuation | 0.832% / 0.639% / 0.542% | True breakout | 41.4% | 27.6% | 31.0% | 2.02x | 1.064% / 0.000% |
| 2024-10-04 10:30 | 7.49x | Full-bodied bullish | Flat / fading | -0.192% / -0.173% / -0.173% | Weak move without breakout | 82.4% | 15.7% | 2.0% | 3.28x | 0.230% / 0.557% |
| 2024-10-04 10:45 | 3.48x | Bearish pin-bar / upper rejection | Reversal | 0.019% / -0.096% / 0.288% | Liquidity sweep / reversal | 25.8% | 45.2% | 29.0% | 1.69x | 0.365% / 0.327% |
| 2024-10-07 10:00 | 12.74x | Small-body bullish | Reversal | -0.195% / -0.527% / -0.605% | Liquidity sweep / reversal | 56.0% | 36.0% | 8.0% | 3.21x | 0.137% / 0.761% |
| 2024-10-07 10:15 | 5.75x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.332% / -0.469% / -0.782% | True breakout | 58.8% | 41.2% | 0.0% | 1.82x | 0.899% / 0.137% |
| 2024-10-07 10:30 | 5.37x | Full-bodied bearish | Impulse / continuation | -0.137% / -0.078% / -0.059% | True breakout | 63.0% | 25.9% | 11.1% | 2.59x | 0.569% / 0.157% |
| 2024-10-07 10:45 | 4.93x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.059% / -0.314% / -0.020% | True breakout | 41.2% | 47.1% | 11.8% | 1.49x | 0.432% / 0.275% |
| 2024-10-07 11:00 | 4.08x | Bearish pin-bar / upper rejection | Reversal | -0.373% / 0.020% / -0.314% | Liquidity sweep / reversal | 17.6% | 52.9% | 29.4% | 1.38x | 0.216% / 0.491% |
| 2024-10-07 12:30 | 2.73x | Small-body bearish | Flat / fading | 0.158% / 0.337% / 0.040% | Position building in range | 58.1% | 11.6% | 30.2% | 2.34x | 0.139% / 0.376% |
| 2024-10-08 10:00 | 9.97x | Small-body bearish | Impulse / continuation | -0.158% / -0.396% / -0.534% | True breakout | 30.0% | 30.0% | 40.0% | 4.16x | 0.712% / 0.059% |
| 2024-10-08 10:15 | 6.82x | Bullish pin-bar / lower rejection | Flat / fading | -0.238% / -0.297% / -0.377% | Weak move without breakout | 24.2% | 9.1% | 66.7% | 3.76x | 0.555% / 0.159% |
| 2024-10-08 10:30 | 4.45x | Bullish pin-bar / lower rejection | Flat / fading | -0.060% / -0.139% / -0.139% | Position building in range | 30.6% | 25.0% | 44.4% | 3.38x | 0.238% / 0.119% |
| 2024-10-08 12:30 | 2.51x | Full-bodied bullish | Impulse / continuation | 0.335% / 0.158% / 0.394% | True breakout | 72.7% | 22.7% | 4.5% | 1.27x | 0.611% / 0.158% |
| 2024-10-09 10:00 | 11.95x | Bearish pin-bar / upper rejection | Reversal | -0.079% / -0.256% / 0.513% | Liquidity sweep / reversal | 4.8% | 61.9% | 33.3% | 4.26x | 0.532% / 0.335% |
| 2024-10-09 10:15 | 6.62x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.178% / 0.000% / 0.355% | False breakout | 36.4% | 9.1% | 54.5% | 1.77x | 0.257% / 0.612% |
| 2024-10-09 10:30 | 6.23x | Bearish pin-bar / upper rejection | Reversal | 0.178% / 0.771% / 0.633% | Liquidity sweep / reversal | 38.1% | 42.9% | 19.0% | 3.23x | 0.040% / 0.791% |
| 2024-10-09 10:45 | 2.62x | Full-bodied bullish | Impulse / continuation | 0.592% / 0.355% / 0.355% | True breakout | 66.7% | 8.3% | 25.0% | 1.51x | 0.612% / 0.039% |
| 2024-10-09 11:00 | 5.15x | Full-bodied bullish | Flat / fading | -0.235% / -0.137% / -0.177% | Position building in range | 90.9% | 3.0% | 6.1% | 3.82x | 0.020% / 0.334% |
| 2024-10-09 11:15 | 2.77x | Full-bodied bearish | Impulse / continuation | 0.098% / 0.000% / -0.236% | True breakout | 72.2% | 0.0% | 27.8% | 1.65x | 0.334% / 0.177% |
| 2024-10-09 14:30 | 17.65x | Full-bodied bullish | Flat / fading | 0.155% / -0.311% / -0.272% | Position building in range | 64.0% | 36.0% | 0.0% | 7.99x | 0.427% / 0.621% |
| 2024-10-09 14:45 | 2.73x | Bearish pin-bar / upper rejection | Reversal | -0.465% / -0.582% / -0.446% | Liquidity sweep / reversal | 29.6% | 51.9% | 18.5% | 1.22x | 0.000% / 0.776% |
| 2024-10-10 10:00 | 8.84x | Bullish pin-bar / lower rejection | Reversal | 0.564% / 0.194% / 0.233% | Liquidity sweep / reversal | 21.4% | 17.9% | 60.7% | 5.03x | 0.272% / 0.797% |
| 2024-10-10 10:15 | 9.52x | Full-bodied bullish | Reversal | -0.367% / -0.599% / -0.309% | Liquidity sweep / reversal | 64.4% | 26.7% | 8.9% | 6.30x | 0.058% / 0.831% |
| 2024-10-10 10:30 | 3.52x | Full-bodied bearish | Impulse / continuation | -0.233% / 0.039% / 0.078% | True breakout | 75.0% | 16.7% | 8.3% | 2.40x | 0.466% / 0.213% |
| 2024-10-10 10:45 | 3.35x | Small-body bearish | Reversal | 0.272% / 0.292% / 0.311% | Liquidity sweep / reversal | 34.3% | 31.4% | 34.3% | 3.08x | 0.058% / 0.408% |
| 2024-10-11 10:00 | 14.83x | Small-body bearish | Flat / fading | -0.020% / -0.039% / -0.020% | Position building in range | 47.6% | 23.8% | 28.6% | 6.39x | 0.117% / 0.078% |
| 2024-10-11 10:15 | 5.74x | Doji | Flat / fading | -0.020% / 0.039% / 0.039% | Weak move without breakout | 0.0% | 44.4% | 55.6% | 1.94x | 0.098% / 0.098% |
| 2024-10-11 10:30 | 4.13x | Doji / upper rejection | Flat / fading | 0.059% / 0.020% / 0.078% | Position building in range | 0.0% | 75.0% | 25.0% | 1.56x | 0.117% / 0.117% |
| 2024-10-11 10:45 | 3.00x | Small-body bullish | Flat / fading | -0.039% / 0.000% / 0.058% | Weak move without breakout | 37.5% | 37.5% | 25.0% | 1.44x | 0.156% / 0.058% |
| 2024-10-11 13:15 | 2.60x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.039% / -0.078% / -0.313% | True breakout | 33.3% | 22.2% | 44.4% | 1.19x | 0.586% / 0.117% |
| 2024-10-11 14:00 | 2.14x | Full-bodied bearish | Flat / fading | 0.137% / 0.157% / 0.196% | Position building in range | 74.1% | 0.0% | 25.9% | 3.90x | 0.039% / 0.236% |
| 2024-10-11 19:45 | 4.87x | Full-bodied bullish | Flat / fading | -0.078% / -0.117% / -0.253% | Weak move without breakout | 69.2% | 23.1% | 7.7% | 4.49x | 0.039% / 0.409% |
| 2024-10-14 10:00 | 6.25x | Full-bodied bearish | Impulse / continuation | -0.196% / -0.176% / -0.176% | True breakout | 64.7% | 0.0% | 35.3% | 2.56x | 0.549% / 0.039% |
| 2024-10-14 10:15 | 7.04x | Bullish pin-bar / lower rejection | Flat / fading | 0.020% / 0.098% / -0.138% | Position building in range | 33.3% | 6.7% | 60.0% | 4.16x | 0.196% / 0.177% |
| 2024-10-14 12:45 | 3.05x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.098% / 0.470% / 0.529% | True breakout | 20.0% | 70.0% | 10.0% | 0.69x | 0.881% / 0.039% |
| 2024-10-14 13:15 | 3.07x | Full-bodied bullish | Flat / fading | 0.273% / 0.058% / 0.175% | Weak move without breakout | 70.4% | 25.9% | 3.7% | 1.89x | 0.409% / 0.156% |
| 2024-10-14 13:30 | 3.08x | Small-body bullish | Flat / fading | -0.214% / 0.039% / 0.058% | Position building in range | 44.8% | 24.1% | 31.0% | 1.95x | 0.136% / 0.311% |
| 2024-10-14 16:00 | 2.34x | Full-bodied bullish | Flat / fading | 0.000% / 0.251% / 0.271% | Weak move without breakout | 70.6% | 20.6% | 8.8% | 2.07x | 0.368% / 0.174% |
| 2024-10-15 10:00 | 10.49x | Small-body bullish | Impulse / continuation | -0.134% / 0.498% / 0.786% | True breakout | 41.7% | 27.1% | 31.3% | 3.95x | 0.824% / 0.441% |
| 2024-10-15 10:15 | 4.25x | Bullish pin-bar / lower rejection | Reversal | 0.634% / 0.422% / 1.113% | Liquidity sweep / reversal | 33.3% | 0.0% | 66.7% | 1.62x | 0.038% / 1.286% |
| 2024-10-15 10:30 | 6.13x | Full-bodied bullish | Impulse / continuation | -0.210% / 0.286% / 0.343% | True breakout | 78.0% | 14.6% | 7.3% | 2.71x | 0.649% / 0.439% |
| 2024-10-15 11:00 | 3.33x | Full-bodied bullish | Flat / fading | 0.190% / 0.057% / -0.133% | Weak move without breakout | 65.0% | 5.0% | 30.0% | 2.22x | 0.361% / 0.190% |
| 2024-10-15 11:15 | 2.77x | Small-body bullish | Reversal | -0.133% / -0.190% / -0.418% | Liquidity sweep / reversal | 42.3% | 34.6% | 23.1% | 1.41x | 0.038% / 0.589% |
| 2024-10-16 10:00 | 14.40x | Bearish pin-bar / upper rejection | Flat / fading | -0.019% / -0.076% / 0.076% | Weak move without breakout | 48.0% | 40.0% | 12.0% | 4.61x | 0.228% / 0.152% |
| 2024-10-16 10:15 | 4.58x | Bearish pin-bar / upper rejection | Reversal | -0.057% / 0.152% / 0.076% | Liquidity sweep / reversal | 12.5% | 43.8% | 43.8% | 2.43x | 0.095% / 0.247% |
| 2024-10-16 10:45 | 4.27x | Full-bodied bullish | Reversal | -0.057% / -0.076% / -0.190% | Liquidity sweep / reversal | 64.7% | 29.4% | 5.9% | 2.27x | 0.019% / 0.361% |
| 2024-10-16 11:30 | 3.07x | Full-bodied bearish | Impulse / continuation | 0.095% / 0.038% / -0.247% | True breakout | 66.7% | 6.7% | 26.7% | 1.67x | 0.285% / 0.171% |
| 2024-10-16 12:45 | 3.35x | Full-bodied bearish | Flat / fading | -0.249% / 0.172% / 0.038% | Weak move without breakout | 88.0% | 0.0% | 12.0% | 2.06x | 0.268% / 0.268% |
| 2024-10-17 10:00 | 9.34x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / -0.019% / -0.019% | Weak move without breakout | 5.0% | 40.0% | 55.0% | 3.68x | 0.173% / 0.230% |
| 2024-10-17 10:15 | 5.24x | Bearish pin-bar / upper rejection | Flat / fading | -0.019% / 0.000% / 0.058% | Weak move without breakout | 6.3% | 56.2% | 37.5% | 2.46x | 0.173% / 0.230% |
| 2024-10-17 10:30 | 3.75x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.019% / 0.000% / 0.019% | False breakout | 18.2% | 72.7% | 9.1% | 1.50x | 0.211% / 0.115% |
| 2024-10-17 10:45 | 3.08x | Bullish pin-bar / lower rejection | Flat / fading | -0.019% / 0.058% / -0.019% | Weak move without breakout | 7.1% | 14.3% | 78.6% | 1.81x | 0.096% / 0.134% |
| 2024-10-18 10:00 | 6.45x | Doji | Impulse / continuation | -0.116% / -0.213% / 0.233% | True breakout | 0.0% | 45.5% | 54.5% | 3.02x | 0.349% / 0.349% |
| 2024-10-18 10:15 | 3.40x | Bearish pin-bar / upper rejection | Reversal | -0.097% / 0.136% / 0.253% | Liquidity sweep / reversal | 37.5% | 43.8% | 18.7% | 1.91x | 0.194% / 0.466% |
| 2024-10-18 10:30 | 5.73x | Bullish pin-bar / lower rejection | Reversal | 0.233% / 0.447% / 0.369% | Liquidity sweep / reversal | 33.3% | 25.0% | 41.7% | 1.31x | 0.058% / 0.564% |
| 2024-10-18 10:45 | 3.35x | Full-bodied bullish | Impulse / continuation | 0.213% / 0.116% / 0.097% | True breakout | 75.0% | 6.3% | 18.7% | 1.76x | 0.330% / 0.039% |
| 2024-10-18 11:00 | 4.52x | Small-body bullish | Flat / fading | -0.097% / -0.077% / -0.097% | Position building in range | 57.9% | 31.6% | 10.5% | 2.00x | 0.039% / 0.232% |
| 2024-10-18 13:45 | 2.13x | Bullish pin-bar / lower rejection | Flat / fading | -0.136% / -0.156% / -0.078% | Weak move without breakout | 38.1% | 14.3% | 47.6% | 1.77x | 0.370% / 0.078% |
| 2024-10-21 10:00 | 13.28x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.233% / 0.174% / 0.271% | True breakout | 36.0% | 56.0% | 8.0% | 5.56x | 0.368% / 0.019% |
| 2024-10-21 10:15 | 5.81x | Full-bodied bullish | Flat / fading | -0.058% / 0.000% / -0.058% | Position building in range | 60.0% | 35.0% | 5.0% | 3.29x | 0.135% / 0.155% |
| 2024-10-21 10:30 | 3.82x | Bearish pin-bar / upper rejection | Reversal | 0.058% / 0.097% / 0.058% | Liquidity sweep / reversal | 20.0% | 46.7% | 33.3% | 2.14x | 0.077% / 0.193% |
| 2024-10-21 10:45 | 3.16x | Bearish pin-bar / upper rejection | Flat / fading | 0.039% / -0.058% / -0.058% | Weak move without breakout | 25.0% | 41.7% | 33.3% | 1.51x | 0.135% / 0.116% |
| 2024-10-21 11:00 | 3.66x | Bearish pin-bar / upper rejection | Reversal | -0.097% / -0.039% / -0.039% | Liquidity sweep / reversal | 33.3% | 55.6% | 11.1% | 1.08x | 0.039% / 0.155% |
| 2024-10-21 13:15 | 3.45x | Bearish pin-bar / upper rejection | Reversal | -0.019% / 0.038% / -0.231% | Liquidity sweep / reversal | 37.0% | 59.3% | 3.7% | 2.28x | 0.096% / 0.365% |
| 2024-10-22 10:00 | 14.22x | Small-body bearish | Impulse / continuation | -0.116% / -0.348% / -0.463% | True breakout | 33.3% | 33.3% | 33.3% | 2.95x | 0.695% / 0.019% |
| 2024-10-22 10:15 | 7.70x | Small-body bearish | Impulse / continuation | -0.232% / -0.425% / -0.445% | True breakout | 45.5% | 18.2% | 36.4% | 2.23x | 0.580% / 0.000% |
| 2024-10-22 10:30 | 8.64x | Full-bodied bearish | Impulse / continuation | -0.194% / -0.116% / -0.213% | True breakout | 70.6% | 0.0% | 29.4% | 3.09x | 0.349% / 0.078% |
| 2024-10-22 10:45 | 5.32x | Small-body bearish | Flat / fading | 0.078% / -0.019% / 0.058% | Position building in range | 45.5% | 18.2% | 36.4% | 3.42x | 0.117% / 0.252% |
| 2024-10-22 11:00 | 4.05x | Bearish pin-bar / upper rejection | Reversal | -0.097% / -0.097% / 0.000% | Liquidity sweep / reversal | 21.4% | 64.3% | 14.3% | 1.78x | 0.097% / 0.194% |
| 2024-10-22 12:15 | 4.21x | Full-bodied bullish | Reversal | -0.116% / -0.193% / -0.290% | Liquidity sweep / reversal | 75.0% | 25.0% | 0.0% | 1.85x | 0.135% / 0.368% |
| 2024-10-22 18:00 | 2.67x | Small-body bearish | Flat / fading | 0.019% / 0.000% / -0.039% | Position building in range | 50.0% | 11.1% | 38.9% | 2.31x | 0.097% / 0.097% |
| 2024-10-23 10:00 | 17.23x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.138% / -0.373% / -0.216% | True breakout | 51.5% | 6.1% | 42.4% | 8.25x | 0.707% / 0.039% |
| 2024-10-23 10:15 | 5.94x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.236% / -0.275% / -0.256% | True breakout | 43.8% | 12.5% | 43.8% | 2.64x | 0.571% / 0.039% |
| 2024-10-23 10:30 | 4.91x | Small-body bearish | Impulse / continuation | -0.039% / 0.158% / -0.059% | True breakout | 60.0% | 5.0% | 35.0% | 2.89x | 0.335% / 0.276% |
| 2024-10-23 10:45 | 5.01x | Bullish pin-bar / lower rejection | Reversal | 0.197% / 0.020% / -0.020% | Liquidity sweep / reversal | 3.8% | 38.5% | 57.7% | 3.28x | 0.217% / 0.316% |
| 2024-10-23 11:00 | 3.30x | Bullish pin-bar / lower rejection | Flat / fading | -0.177% / -0.217% / -0.138% | Weak move without breakout | 47.8% | 8.7% | 43.5% | 2.40x | 0.118% / 0.354% |
| 2024-10-23 20:30 | 3.16x | Bullish pin-bar / lower rejection | Flat / fading | 0.040% / 0.020% / -0.160% | Weak move without breakout | 46.2% | 7.7% | 46.2% | 1.42x | 0.279% / 0.140% |
| 2024-10-23 22:00 | 7.93x | Bullish pin-bar / lower rejection | Flat / fading | 0.121% / -0.020% / 0.000% | Position building in range | 29.0% | 6.5% | 64.5% | 5.95x | 0.201% / 0.242% |
| 2024-10-24 10:00 | 4.43x | Bearish pin-bar / upper rejection | Flat / fading | 0.423% / 0.362% / 0.362% | Weak move without breakout | 21.6% | 64.9% | 13.5% | 2.44x | 0.785% / 0.060% |
| 2024-10-24 10:15 | 3.28x | Bearish pin-bar / upper rejection | Flat / fading | -0.060% / -0.120% / 0.080% | Position building in range | 50.0% | 42.9% | 7.1% | 2.41x | 0.321% / 0.261% |
| 2024-10-24 11:30 | 3.18x | Full-bodied bullish | Reversal | -0.100% / -0.279% / -0.679% | Liquidity sweep / reversal | 65.4% | 26.9% | 7.7% | 1.54x | 0.060% / 0.779% |
| 2024-10-25 10:00 | 12.33x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.079% / -0.138% / 0.059% | True breakout | 21.1% | 57.9% | 21.1% | 4.29x | 0.217% / 0.138% |
| 2024-10-25 10:15 | 4.39x | Bullish pin-bar / lower rejection | Reversal | -0.059% / -0.040% / 0.079% | Liquidity sweep / reversal | 23.1% | 23.1% | 53.8% | 2.30x | 0.099% / 0.217% |
| 2024-10-25 10:30 | 2.58x | Bearish pin-bar / upper rejection | Reversal | 0.020% / 0.198% / 0.040% | Liquidity sweep / reversal | 27.3% | 54.5% | 18.2% | 1.73x | 0.020% / 0.277% |
| 2024-10-25 13:30 | 12.02x | Bullish pin-bar / lower rejection | Reversal | 0.776% / 0.616% / 0.139% | Liquidity sweep / reversal | 32.4% | 2.8% | 64.8% | 5.23x | 0.179% / 1.332% |
| 2024-10-25 13:45 | 4.93x | Small-body bullish | Flat / fading | -0.158% / -0.197% / -0.750% | Position building in range | 50.0% | 36.8% | 13.2% | 4.40x | 0.355% / 0.908% |
| 2024-10-25 14:15 | 2.72x | Bearish pin-bar / upper rejection | Flat / fading | -0.435% / -0.554% / -0.435% | Weak move without breakout | 3.8% | 50.0% | 46.2% | 2.19x | 0.712% / 0.000% |
| 2024-10-25 16:45 | 2.66x | Small-body bearish | Impulse / continuation | -1.078% / -0.610% / -0.915% | True breakout | 53.9% | 13.2% | 32.9% | 2.06x | 1.302% / 0.386% |
| 2024-10-25 17:00 | 2.44x | Full-bodied bearish | Flat / fading | 0.473% / 0.863% / 0.555% | Position building in range | 61.4% | 25.3% | 13.3% | 2.09x | -0.021% / 1.131% |
| 2024-10-25 19:45 | 3.89x | Full-bodied bearish | Flat / fading | 0.417% / 0.521% / 0.751% | Position building in range | 88.9% | 4.8% | 6.3% | 1.85x | 0.083% / 0.897% |
| 2024-10-28 10:00 | 5.64x | Bearish pin-bar / upper rejection | Reversal | -0.190% / -0.105% / 0.190% | Liquidity sweep / reversal | 14.0% | 54.0% | 32.0% | 3.76x | 0.612% / 0.274% |
| 2024-10-28 10:15 | 3.42x | Bullish pin-bar / lower rejection | Reversal | 0.085% / 0.021% / 0.634% | Liquidity sweep / reversal | 30.6% | 13.9% | 55.6% | 2.25x | 0.275% / 0.739% |
| 2024-10-28 11:15 | 2.55x | Small-body bullish | Impulse / continuation | -0.021% / -0.021% / -0.063% | True breakout | 54.2% | 20.8% | 25.0% | 1.18x | 0.609% / 0.315% |
| 2024-10-29 10:00 | 6.22x | Bearish pin-bar / upper rejection | Reversal | 0.214% / 0.236% / -0.278% | Liquidity sweep / reversal | 27.6% | 48.3% | 24.1% | 2.86x | 0.514% / 0.450% |
| 2024-10-29 10:15 | 4.31x | Bearish pin-bar / upper rejection | Reversal | 0.021% / -0.043% / -0.577% | Liquidity sweep / reversal | 37.5% | 58.3% | 4.2% | 2.09x | 0.235% / 0.769% |
| 2024-10-29 10:30 | 4.80x | Bullish pin-bar / lower rejection | Reversal | -0.064% / -0.513% / -0.876% | Liquidity sweep / reversal | 3.7% | 25.9% | 70.4% | 2.21x | 0.214% / 1.111% |
| 2024-10-29 10:45 | 3.41x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.449% / -0.535% / -0.812% | True breakout | 13.0% | 43.5% | 43.5% | 1.86x | 1.048% / 0.021% |
| 2024-10-29 12:15 | 2.54x | Full-bodied bullish | Flat / fading | -0.472% / -0.236% / -0.215% | Position building in range | 87.5% | 9.4% | 3.1% | 1.75x | 0.043% / 0.580% |
| 2024-10-29 22:00 | 3.05x | Small-body bullish | Reversal | -0.334% / -0.501% / -0.605% | Liquidity sweep / reversal | 58.3% | 39.6% | 2.1% | 5.05x | 0.063% / 0.668% |
| 2024-10-30 10:00 | 9.27x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.376% / -0.292% / 0.167% | False breakout | 15.0% | 62.5% | 22.5% | 2.76x | 0.835% / 0.334% |
| 2024-10-30 10:15 | 3.97x | Full-bodied bearish | Reversal | 0.084% / 0.231% / 0.126% | Liquidity sweep / reversal | 60.0% | 0.0% | 40.0% | 1.80x | 0.461% / 0.712% |
| 2024-10-30 10:30 | 3.74x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.147% / 0.461% / 0.042% | True breakout | 13.8% | 10.3% | 75.9% | 1.58x | 0.628% / 0.230% |
| 2024-10-30 10:45 | 2.82x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.314% / -0.105% / -0.209% | False breakout | 31.6% | 5.3% | 63.2% | 0.95x | 0.481% / 0.335% |
| 2024-10-30 11:00 | 2.66x | Small-body bullish | Reversal | -0.417% / -0.417% / -0.188% | Liquidity sweep / reversal | 58.3% | 33.3% | 8.3% | 1.17x | 0.042% / 0.646% |
| 2024-10-31 10:00 | 5.63x | Full-bodied bullish | Flat / fading | -0.128% / -0.086% / 0.086% | Weak move without breakout | 63.0% | 33.3% | 3.7% | 1.58x | 0.278% / 0.171% |
| 2024-10-31 10:15 | 3.13x | Bearish pin-bar / upper rejection | Reversal | 0.043% / 0.214% / 0.514% | Liquidity sweep / reversal | 33.3% | 57.1% | 9.5% | 1.14x | 0.021% / 0.643% |
| 2024-11-01 10:00 | 5.85x | Full-bodied bullish | Reversal | -0.163% / 0.094% / -0.462% | Liquidity sweep / reversal | 61.5% | 38.5% | 0.0% | 2.82x | 0.137% / 0.505% |
| 2024-11-01 10:15 | 6.17x | Bullish pin-bar / lower rejection | Reversal | 0.257% / -0.034% / -0.437% | Liquidity sweep / reversal | 32.7% | 0.0% | 67.3% | 2.15x | 0.617% / 0.300% |
| 2024-11-01 10:30 | 3.26x | Full-bodied bullish | Reversal | -0.291% / -0.556% / -0.693% | Liquidity sweep / reversal | 80.6% | 13.9% | 5.6% | 1.36x | 0.034% / 0.872% |
| 2024-11-02 10:00 | 7.77x | Full-bodied bullish | Flat / fading | -0.179% / -0.187% / -0.179% | Position building in range | 76.9% | 15.4% | 7.7% | 3.64x | 0.034% / 0.247% |
| 2024-11-02 10:15 | 5.06x | Full-bodied bearish | Flat / fading | -0.009% / 0.111% / -0.017% | Weak move without breakout | 84.0% | 16.0% | 0.0% | 1.94x | 0.068% / 0.145% |
| 2024-11-02 10:45 | 3.11x | Full-bodied bullish | Reversal | -0.111% / -0.128% / -0.281% | Liquidity sweep / reversal | 65.0% | 20.0% | 15.0% | 1.57x | 0.026% / 0.340% |
| 2024-11-02 17:15 | 2.33x | Small-body bearish | Impulse / continuation | -0.534% / -0.319% / -0.663% | True breakout | 38.9% | 25.0% | 36.1% | 1.40x | 0.844% / 0.017% |
| 2024-11-02 17:30 | 3.62x | Full-bodied bearish | Impulse / continuation | 0.216% / 0.000% / -0.199% | True breakout | 84.9% | 2.7% | 12.3% | 2.68x | 0.476% / 0.381% |
| 2024-11-02 17:45 | 2.73x | Bearish pin-bar / upper rejection | Reversal | -0.216% / -0.346% / -0.899% | Liquidity sweep / reversal | 57.4% | 40.4% | 2.1% | 1.56x | 0.009% / 0.899% |
| 2024-11-02 18:00 | 2.23x | Full-bodied bearish | Impulse / continuation | -0.130% / -0.199% / -0.303% | True breakout | 60.5% | 0.0% | 39.5% | 1.41x | 0.684% / 0.078% |
| 2024-11-02 18:15 | 2.57x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.069% / -0.555% / -0.043% | True breakout | 33.3% | 20.0% | 46.7% | 1.41x | 0.555% / 0.234% |
| 2024-11-05 10:00 | 7.55x | Bullish pin-bar / lower rejection | Reversal | -0.540% / -0.720% / -0.695% | Liquidity sweep / reversal | 44.6% | 12.2% | 43.2% | 2.76x | 0.026% / 0.935% |
| 2024-11-05 10:15 | 5.95x | Full-bodied bearish | Impulse / continuation | -0.181% / -0.207% / 0.060% | True breakout | 94.1% | 2.9% | 2.9% | 2.27x | 0.397% / 0.155% |
| 2024-11-05 10:30 | 4.90x | Bullish pin-bar / lower rejection | Reversal | -0.026% / 0.026% / 0.259% | Liquidity sweep / reversal | 43.6% | 10.9% | 45.5% | 1.67x | 0.207% / 0.458% |
| 2024-11-06 10:00 | 50.43x | Bullish pin-bar / lower rejection | Reversal | -0.638% / -0.091% / 0.415% | Liquidity sweep / reversal | 27.3% | 29.7% | 43.0% | 4.82x | 0.929% / 1.111% |
| 2024-11-06 10:15 | 9.24x | Small-body bearish | Reversal | 0.551% / 0.985% / 0.676% | Liquidity sweep / reversal | 49.1% | 16.0% | 35.0% | 3.46x | 0.200% / 1.577% |
| 2024-11-06 10:30 | 3.40x | Full-bodied bullish | Impulse / continuation | 0.432% / 0.506% / 0.357% | True breakout | 67.7% | 6.2% | 26.0% | 1.66x | 1.021% / 0.207% |
| 2024-11-06 10:45 | 5.52x | Bearish pin-bar / upper rejection | Flat / fading | 0.074% / -0.306% / -0.273% | Weak move without breakout | 41.5% | 57.7% | 0.8% | 1.92x | 0.297% / 0.636% |
| 2024-11-07 12:00 | 2.69x | Full-bodied bearish | Impulse / continuation | -0.068% / -0.330% / -0.533% | True breakout | 70.7% | 25.9% | 3.4% | 2.69x | 0.575% / 0.110% |
| 2024-11-07 12:15 | 5.36x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.262% / -0.161% / -0.423% | True breakout | 15.4% | 25.0% | 59.6% | 2.38x | 0.508% / 0.102% |
| 2024-11-07 12:30 | 3.46x | Full-bodied bearish | Impulse / continuation | 0.102% / -0.204% / -0.102% | True breakout | 69.6% | 23.9% | 6.5% | 2.04x | 0.246% / 0.212% |
| 2024-11-07 12:45 | 3.38x | Bearish pin-bar / upper rejection | Reversal | -0.305% / -0.263% / -0.356% | Liquidity sweep / reversal | 43.3% | 43.3% | 13.3% | 1.26x | 0.017% / 0.415% |
| 2024-11-07 13:00 | 2.77x | Full-bodied bearish | Flat / fading | 0.042% / 0.102% / 0.144% | Weak move without breakout | 86.0% | 2.3% | 11.6% | 1.74x | 0.110% / 0.204% |
| 2024-11-07 14:45 | 2.81x | Small-body bullish | Impulse / continuation | 0.228% / 0.489% / 0.776% | True breakout | 37.5% | 25.0% | 37.5% | 1.98x | 0.978% / 0.093% |
| 2024-11-07 15:00 | 2.85x | Small-body bullish | Impulse / continuation | 0.261% / 0.379% / 0.412% | True breakout | 46.6% | 34.5% | 19.0% | 1.61x | 0.749% / 0.000% |
| 2024-11-07 15:15 | 3.35x | Bearish pin-bar / upper rejection | Flat / fading | 0.117% / 0.285% / 0.059% | Weak move without breakout | 46.2% | 52.3% | 1.5% | 1.64x | 0.487% / 0.076% |
| 2024-11-07 17:00 | 1.97x | Full-bodied bullish | Impulse / continuation | 0.284% / 0.492% / 1.017% | True breakout | 77.9% | 19.1% | 2.9% | 1.57x | 1.134% / 0.359% |
| 2024-11-07 17:30 | 2.54x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.407% / 0.523% / 0.589% | True breakout | 42.9% | 53.6% | 3.6% | 1.09x | 1.012% / 0.158% |
| 2024-11-07 17:45 | 1.99x | Small-body bullish | Flat / fading | 0.116% / 0.504% / 0.331% | Weak move without breakout | 56.2% | 23.6% | 20.2% | 1.69x | 0.603% / 0.149% |
| 2024-11-07 18:15 | 2.18x | Small-body bullish | Flat / fading | -0.321% / -0.173% / 0.189% | Weak move without breakout | 52.9% | 14.1% | 32.9% | 1.52x | 0.197% / 0.518% |
| 2024-11-08 10:00 | 5.39x | Full-bodied bearish | Reversal | 0.144% / 0.912% / 1.416% | Liquidity sweep / reversal | 72.5% | 2.5% | 25.0% | 2.43x | 0.352% / 1.800% |
| 2024-11-08 10:30 | 2.72x | Full-bodied bullish | Impulse / continuation | 0.452% / 0.500% / -0.428% | True breakout | 82.1% | 5.1% | 12.8% | 1.95x | 0.880% / 0.436% |
| 2024-11-08 10:45 | 4.25x | Small-body bullish | Reversal | 0.047% / -0.600% / -0.939% | Liquidity sweep / reversal | 38.5% | 30.4% | 31.1% | 2.21x | 0.426% / 1.192% |
| 2024-11-08 11:00 | 3.06x | Bearish pin-bar / upper rejection | Reversal | -0.647% / -0.923% / -1.065% | Liquidity sweep / reversal | 8.0% | 54.5% | 37.5% | 1.18x | 0.039% / 1.278% |
| 2024-11-08 19:00 | 3.01x | Bearish pin-bar / upper rejection | Flat / fading | 0.142% / -0.158% / 0.016% | Position building in range | 44.5% | 48.2% | 7.3% | 2.23x | 0.221% / 0.268% |
| 2024-11-11 10:00 | 7.87x | Full-bodied bearish | Flat / fading | 0.146% / 0.384% / 0.622% | Weak move without breakout | 85.1% | 14.2% | 0.7% | 2.90x | 0.338% / 0.837% |
| 2024-11-11 10:15 | 3.31x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.238% / 0.238% / 0.728% | True breakout | 19.4% | 38.8% | 41.7% | 1.82x | 0.805% / 0.000% |
| 2024-11-11 10:30 | 2.78x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.000% / 0.237% / 0.604% | True breakout | 38.7% | 61.3% | 0.0% | 1.31x | 0.849% / 0.069% |
| 2024-11-11 12:00 | 3.12x | Full-bodied bearish | Flat / fading | 0.160% / 0.267% / 0.275% | Position building in range | 78.1% | 6.2% | 15.6% | 1.67x | 0.076% / 0.412% |
| 2024-11-12 10:00 | 16.98x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.200% / -0.546% / -0.369% | True breakout | 49.4% | 1.3% | 49.4% | 6.11x | 0.823% / 0.262% |
| 2024-11-12 10:15 | 6.76x | Small-body bearish | Impulse / continuation | -0.347% / -0.432% / -0.023% | True breakout | 41.3% | 38.1% | 20.6% | 3.54x | 0.624% / 0.462% |
| 2024-11-12 10:30 | 7.07x | Full-bodied bearish | Flat / fading | -0.085% / 0.178% / 0.008% | Weak move without breakout | 61.6% | 1.4% | 37.0% | 3.34x | 0.278% / 0.812% |
| 2024-11-12 10:45 | 4.92x | Bullish pin-bar / lower rejection | Reversal | 0.263% / 0.410% / 0.279% | Liquidity sweep / reversal | 22.9% | 25.0% | 52.1% | 1.83x | 0.085% / 0.898% |
| 2024-11-12 11:00 | 5.75x | Bearish pin-bar / upper rejection | Flat / fading | 0.147% / -0.170% / 0.139% | Position building in range | 26.8% | 64.6% | 8.7% | 4.47x | 0.486% / 0.185% |
| 2024-11-13 10:00 | 5.29x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.259% / 0.134% / 0.527% | True breakout | 10.1% | 20.3% | 69.6% | 2.50x | 0.707% / 0.141% |
| 2024-11-13 10:15 | 2.88x | Full-bodied bullish | Impulse / continuation | -0.125% / -0.219% / 0.298% | True breakout | 67.3% | 14.3% | 18.4% | 1.62x | 0.604% / 0.400% |
| 2024-11-13 11:00 | 3.47x | Full-bodied bullish | Impulse / continuation | 0.031% / 0.266% / 0.500% | True breakout | 69.2% | 25.3% | 5.5% | 2.92x | 0.641% / 0.039% |
| 2024-11-13 11:45 | 2.26x | Full-bodied bullish | Flat / fading | -0.039% / 0.225% / -0.148% | Weak move without breakout | 62.5% | 23.2% | 14.3% | 1.47x | 0.334% / 0.194% |
| 2024-11-13 19:00 | 3.98x | Small-body bearish | Impulse / continuation | -0.440% / -0.786% / -0.928% | True breakout | 49.5% | 12.8% | 37.6% | 3.25x | 1.218% / 0.110% |
| 2024-11-13 19:30 | 3.26x | Full-bodied bearish | Flat / fading | -0.024% / -0.143% / 0.222% | Weak move without breakout | 62.5% | 0.0% | 37.5% | 1.57x | 0.436% / 0.333% |
| 2024-11-14 10:00 | 4.20x | Full-bodied bullish | Flat / fading | 0.024% / -0.228% / 0.024% | Position building in range | 64.4% | 22.0% | 13.6% | 5.11x | 0.181% / 0.267% |
| 2024-11-14 11:15 | 3.17x | Full-bodied bullish | Impulse / continuation | 0.258% / 0.266% / 0.446% | True breakout | 64.4% | 30.5% | 5.1% | 1.87x | 0.728% / 0.016% |
| 2024-11-14 12:00 | 2.53x | Full-bodied bullish | Flat / fading | -0.156% / -0.125% / 0.210% | Weak move without breakout | 71.7% | 26.7% | 1.7% | 1.56x | 0.241% / 0.327% |
| 2024-11-15 10:00 | 8.53x | Bullish pin-bar / lower rejection | Reversal | -0.280% / -0.241% / -0.405% | Liquidity sweep / reversal | 23.1% | 32.7% | 44.2% | 2.27x | 0.016% / 0.452% |
| 2024-11-15 10:15 | 3.93x | Full-bodied bearish | Flat / fading | 0.039% / 0.031% / -0.148% | Weak move without breakout | 78.3% | 4.3% | 17.4% | 1.79x | 0.250% / 0.211% |
| 2024-11-15 11:30 | 3.27x | Small-body bullish | Flat / fading | 0.226% / 0.179% / 0.203% | Weak move without breakout | 54.8% | 35.5% | 9.7% | 2.03x | 0.406% / 0.234% |
| 2024-11-15 11:45 | 2.73x | Bullish pin-bar / lower rejection | Reversal | -0.047% / 0.008% / -0.288% | Liquidity sweep / reversal | 37.3% | 21.3% | 41.3% | 2.25x | 0.179% / 0.397% |
| 2024-11-15 15:45 | 2.99x | Bearish pin-bar / upper rejection | Flat / fading | 0.031% / -0.086% / 0.055% | Position building in range | 34.4% | 63.9% | 1.6% | 2.18x | 0.226% / 0.086% |
| 2024-11-18 10:00 | 6.84x | Full-bodied bullish | Impulse / continuation | 0.366% / 0.809% / 0.793% | True breakout | 67.9% | 6.0% | 26.1% | 5.01x | 0.980% / 0.194% |
| 2024-11-18 10:15 | 4.75x | Small-body bullish | Impulse / continuation | 0.442% / 0.186% / 0.814% | True breakout | 55.8% | 16.3% | 27.9% | 1.51x | 1.015% / 0.016% |
| 2024-11-18 10:30 | 4.71x | Full-bodied bullish | Flat / fading | -0.255% / -0.015% / 0.116% | Weak move without breakout | 70.4% | 27.2% | 2.5% | 1.31x | 0.571% / 0.262% |
| 2024-11-18 16:45 | 2.56x | Full-bodied bullish | Impulse / continuation | 0.685% / 1.085% / 1.315% | True breakout | 78.9% | 14.5% | 6.6% | 2.48x | 1.815% / 0.192% |
| 2024-11-18 17:00 | 4.17x | Full-bodied bullish | Impulse / continuation | 0.397% / 0.718% / 0.680% | True breakout | 61.4% | 21.4% | 17.2% | 4.33x | 1.123% / 0.099% |
| 2024-11-18 17:15 | 3.14x | Full-bodied bullish | Impulse / continuation | 0.320% / 0.228% / 1.164% | True breakout | 70.8% | 9.7% | 19.4% | 1.75x | 1.240% / 0.038% |
| 2024-11-18 17:30 | 4.02x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.091% / -0.038% / 0.652% | True breakout | 42.4% | 53.5% | 4.0% | 2.23x | 0.918% / 0.356% |
| 2024-11-18 18:15 | 2.77x | Full-bodied bullish | Flat / fading | -0.188% / -0.338% / -0.474% | Position building in range | 79.7% | 6.8% | 13.5% | 2.84x | 0.030% / 0.895% |
| 2024-11-19 10:00 | 4.29x | Bearish pin-bar / upper rejection | Flat / fading | 0.429% / 0.218% / -0.060% | Position building in range | 11.2% | 67.2% | 21.6% | 2.24x | 0.504% / 0.241% |
| 2024-11-19 17:15 | 2.55x | Bullish pin-bar / lower rejection | Reversal | 0.326% / 0.163% / 1.062% | Liquidity sweep / reversal | 44.7% | 7.3% | 48.0% | 2.13x | 0.186% / 1.263% |
| 2024-11-20 10:00 | 10.09x | Bearish pin-bar / upper rejection | Reversal | 0.207% / -0.314% / -0.390% | Liquidity sweep / reversal | 38.4% | 51.5% | 10.1% | 3.22x | 0.344% / 0.597% |
| 2024-11-20 10:15 | 5.71x | Small-body bullish | Reversal | -0.519% / -0.695% / -0.840% | Liquidity sweep / reversal | 48.0% | 36.0% | 16.0% | 1.42x | 0.023% / 0.886% |
| 2024-11-20 10:30 | 3.60x | Full-bodied bearish | Impulse / continuation | -0.177% / -0.077% / -0.353% | True breakout | 86.1% | 3.8% | 10.1% | 2.13x | 0.699% / 0.169% |
| 2024-11-20 10:45 | 2.93x | Small-body bearish | Impulse / continuation | 0.100% / -0.146% / -0.069% | True breakout | 43.6% | 30.9% | 25.5% | 1.39x | 0.523% / 0.346% |
| 2024-11-20 19:00 | 2.60x | Bearish pin-bar / upper rejection | Reversal | 0.008% / -0.118% / 0.016% | Liquidity sweep / reversal | 3.8% | 59.0% | 37.2% | 1.63x | 0.606% / 0.417% |
| 2024-11-21 10:00 | 4.83x | Bearish pin-bar / upper rejection | Reversal | 0.149% / -0.462% / -0.517% | Liquidity sweep / reversal | 20.0% | 44.3% | 35.7% | 2.68x | 0.211% / 1.081% |
| 2024-11-21 10:15 | 2.83x | Small-body bullish | Reversal | -0.610% / -0.986% / -0.978% | Liquidity sweep / reversal | 48.7% | 20.5% | 30.8% | 1.43x | 0.016% / 1.228% |
| 2024-11-21 10:30 | 5.24x | Full-bodied bearish | Impulse / continuation | -0.378% / -0.055% / -0.842% | True breakout | 74.8% | 2.9% | 22.3% | 3.70x | 0.944% / 0.165% |
| 2024-11-21 10:45 | 3.70x | Small-body bearish | Impulse / continuation | 0.324% / 0.008% / -0.592% | True breakout | 53.9% | 23.6% | 22.5% | 2.67x | 0.743% / 0.411% |
| 2024-11-21 11:00 | 2.80x | Bullish pin-bar / lower rejection | Reversal | -0.315% / -0.787% / -0.906% | Liquidity sweep / reversal | 53.2% | 6.5% | 40.3% | 2.08x | 0.087% / 1.378% |
| 2024-11-21 11:30 | 2.97x | Full-bodied bearish | Impulse / continuation | -0.127% / -0.119% / -0.143% | True breakout | 76.9% | 6.4% | 16.7% | 1.84x | 0.595% / 0.429% |
| 2024-11-21 12:00 | 2.62x | Doji / lower rejection | Impulse / continuation | 0.540% / -0.024% / 0.191% | True breakout | 0.0% | 14.3% | 85.7% | 1.43x | 0.548% / 0.548% |
| 2024-11-21 18:00 | 2.90x | Full-bodied bullish | Flat / fading | -0.551% / -0.465% / -0.457% | Position building in range | 66.7% | 25.2% | 8.1% | 3.25x | 0.095% / 0.685% |
| 2024-11-21 20:00 | 3.43x | Bullish pin-bar / lower rejection | Reversal | 0.977% / 1.201% / 1.289% | Liquidity sweep / reversal | 53.1% | 5.1% | 41.8% | 6.83x | 0.512% / 1.489% |
| 2024-11-21 20:15 | 2.97x | Full-bodied bullish | Flat / fading | 0.222% / 0.444% / 0.325% | Weak move without breakout | 61.0% | 7.0% | 32.0% | 3.30x | 0.507% / 0.032% |
| 2024-11-22 10:00 | 3.75x | Small-body bearish | Flat / fading | -0.148% / -0.125% / -0.062% | Weak move without breakout | 53.6% | 30.0% | 16.4% | 2.43x | 0.475% / 0.514% |
| 2024-11-22 10:15 | 2.50x | Bullish pin-bar / lower rejection | Reversal | 0.023% / 0.483% / -0.125% | Liquidity sweep / reversal | 23.3% | 27.9% | 48.8% | 1.76x | 0.312% / 0.662% |
| 2024-11-22 17:30 | 2.77x | Bullish pin-bar / lower rejection | Reversal | -3.965% / -1.780% / -2.312% | Liquidity sweep / reversal | 14.2% | 7.5% | 78.3% | 2.20x | 0.064% / 4.171% |
| 2024-11-22 17:45 | 10.95x | Full-bodied bearish | Flat / fading | 2.275% / 1.423% / 1.762% | Position building in range | 93.8% | 1.3% | 4.9% | 9.96x | 0.058% / 2.507% |
| 2024-11-22 18:00 | 5.66x | Full-bodied bullish | Flat / fading | -0.833% / -0.542% / -0.324% | Position building in range | 88.7% | 9.0% | 2.3% | 3.52x | 0.024% / 1.133% |
| 2024-11-25 10:00 | 6.24x | Small-body bearish | Flat / fading | 0.160% / 0.093% / -0.168% | Weak move without breakout | 51.8% | 38.6% | 9.6% | 1.72x | 0.505% / 0.387% |
| 2024-11-25 17:30 | 2.65x | Full-bodied bearish | Flat / fading | 0.034% / 0.249% / 0.549% | Weak move without breakout | 81.8% | 0.0% | 18.2% | 2.15x | 0.069% / 0.900% |
| 2024-11-26 10:00 | 6.57x | Bullish pin-bar / lower rejection | Reversal | 0.282% / 0.821% / 1.232% | Liquidity sweep / reversal | 14.5% | 34.9% | 50.6% | 3.70x | 0.034% / 1.343% |
| 2024-11-26 10:15 | 6.53x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.537% / 0.503% / 0.990% | True breakout | 42.3% | 52.6% | 5.1% | 2.91x | 1.194% / 0.034% |
| 2024-11-26 10:30 | 3.79x | Full-bodied bullish | Impulse / continuation | -0.034% / 0.407% / 0.526% | True breakout | 86.3% | 8.2% | 5.5% | 2.33x | 0.781% / 0.322% |
| 2024-11-26 10:45 | 3.33x | Bullish pin-bar / lower rejection | Reversal | 0.441% / 0.484% / 0.221% | Liquidity sweep / reversal | 9.3% | 11.6% | 79.1% | 1.22x | 0.136% / 0.815% |
| 2024-11-26 11:00 | 3.19x | Full-bodied bullish | Flat / fading | 0.042% / 0.118% / -0.380% | Weak move without breakout | 64.2% | 16.0% | 19.8% | 2.17x | 0.372% / 0.380% |
| 2024-11-26 11:15 | 2.57x | Bearish pin-bar / upper rejection | Reversal | 0.076% / -0.262% / -0.380% | Liquidity sweep / reversal | 11.1% | 44.4% | 44.4% | 1.34x | 0.329% / 0.574% |
| 2024-11-26 15:15 | 3.22x | Bullish pin-bar / lower rejection | Flat / fading | -0.391% / 0.104% / -0.451% | Weak move without breakout | 49.8% | 5.9% | 44.4% | 4.09x | 0.816% / 0.313% |
| 2024-11-27 10:00 | 5.16x | Full-bodied bearish | Impulse / continuation | -1.320% / -1.010% / -1.409% | True breakout | 73.6% | 23.9% | 2.5% | 4.78x | 2.021% / 0.248% |
| 2024-11-27 10:15 | 7.11x | Full-bodied bearish | Impulse / continuation | 0.314% / -0.494% / -0.278% | True breakout | 81.5% | 14.7% | 3.8% | 4.23x | 0.709% / 0.988% |
| 2024-11-27 10:30 | 4.93x | Bearish pin-bar / upper rejection | Reversal | -0.806% / -0.403% / -0.707% | Liquidity sweep / reversal | 28.0% | 56.8% | 15.2% | 2.56x | 0.063% / 1.191% |
| 2024-11-27 10:45 | 4.37x | Full-bodied bearish | Reversal | 0.406% / 0.217% / 1.200% | Liquidity sweep / reversal | 74.4% | 5.8% | 19.8% | 2.08x | 0.388% / 1.200% |
| 2024-11-27 11:00 | 2.84x | Full-bodied bullish | Impulse / continuation | -0.189% / -0.306% / 1.258% | True breakout | 69.2% | 23.1% | 7.7% | 1.03x | 1.546% / 0.791% |
| 2024-11-27 12:00 | 2.65x | Small-body bullish | Impulse / continuation | 1.065% / 2.415% / 1.358% | True breakout | 54.6% | 33.0% | 12.4% | 1.23x | 3.045% / 0.542% |
| 2024-11-27 12:30 | 4.43x | Full-bodied bullish | Flat / fading | -0.676% / -1.031% / -0.451% | Weak move without breakout | 65.7% | 29.3% | 5.0% | 2.50x | 0.546% / 2.011% |
| 2024-11-27 12:45 | 2.77x | Small-body bearish | Impulse / continuation | -0.358% / -0.148% / 0.175% | True breakout | 39.1% | 39.7% | 21.2% | 1.61x | 1.344% / 0.689% |
| 2024-11-27 19:15 | 2.52x | Full-bodied bullish | Flat / fading | -0.051% / -0.670% / -0.076% | Weak move without breakout | 67.4% | 15.7% | 16.9% | 1.93x | 0.280% / 1.094% |
| 2024-11-28 10:00 | 4.57x | Bullish pin-bar / lower rejection | Reversal | -0.942% / -0.758% / 0.317% | Liquidity sweep / reversal | 23.4% | 10.5% | 66.0% | 4.68x | 0.350% / 0.975% |
| 2024-11-28 10:15 | 3.13x | Full-bodied bearish | Reversal | 0.185% / 0.664% / 1.388% | Liquidity sweep / reversal | 94.2% | 2.5% | 3.3% | 2.09x | -0.008% / 1.632% |
| 2024-11-29 10:00 | 7.56x | Bullish pin-bar / lower rejection | Reversal | 0.220% / 0.636% / 0.755% | Liquidity sweep / reversal | 20.3% | 27.5% | 52.2% | 3.74x | 0.119% / 1.111% |
| 2024-11-29 10:15 | 5.10x | Small-body bullish | Impulse / continuation | 0.415% / 0.643% / 1.117% | True breakout | 39.4% | 39.4% | 21.2% | 3.11x | 1.117% / 0.228% |
| 2024-11-29 10:30 | 3.63x | Small-body bullish | Impulse / continuation | 0.228% / 0.118% / 0.506% | True breakout | 56.2% | 14.6% | 29.2% | 3.58x | 1.053% / 0.076% |
| 2024-11-29 10:45 | 5.64x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.109% / 0.471% / 0.639% | True breakout | 41.5% | 44.6% | 13.8% | 2.21x | 0.824% / 0.286% |
| 2024-11-29 11:00 | 2.81x | Small-body bearish | Reversal | 0.581% / 0.387% / 0.690% | Liquidity sweep / reversal | 25.5% | 36.4% | 38.2% | 1.66x | 0.051% / 1.002% |
| 2024-11-29 11:15 | 4.00x | Full-bodied bullish | Impulse / continuation | -0.192% / 0.167% / 0.343% | True breakout | 92.0% | 0.0% | 8.0% | 2.08x | 0.460% / 0.293% |
| 2024-11-29 11:30 | 3.54x | Bearish pin-bar / upper rejection | Reversal | 0.361% / 0.302% / 0.503% | Liquidity sweep / reversal | 31.9% | 58.3% | 9.7% | 1.77x | 0.101% / 0.654% |
| 2024-11-29 11:45 | 2.65x | Small-body bullish | Flat / fading | -0.058% / 0.175% / 0.184% | Weak move without breakout | 59.7% | 23.6% | 16.7% | 1.59x | 0.334% / 0.117% |
| 2024-11-29 12:00 | 2.54x | Bearish pin-bar / upper rejection | Reversal | 0.234% / 0.201% / -0.042% | Liquidity sweep / reversal | 24.3% | 75.7% | 0.0% | 0.75x | 0.234% / 0.393% |
| 2024-12-02 10:00 | 18.59x | Full-bodied bullish | Flat / fading | -0.338% / -0.239% / -0.512% | Position building in range | 68.6% | 28.5% | 2.9% | 6.33x | 0.083% / 0.594% |
| 2024-12-02 10:15 | 6.90x | Full-bodied bearish | Impulse / continuation | 0.099% / 0.050% / -0.356% | True breakout | 73.2% | 7.1% | 19.6% | 1.84x | 0.398% / 0.422% |
| 2024-12-02 10:30 | 3.72x | Bearish pin-bar / upper rejection | Reversal | -0.050% / -0.273% / -0.372% | Liquidity sweep / reversal | 20.7% | 67.2% | 12.1% | 1.77x | 0.232% / 0.612% |
| 2024-12-02 11:00 | 2.92x | Small-body bearish | Impulse / continuation | -0.183% / -0.100% / -0.614% | True breakout | 54.9% | 25.5% | 19.6% | 1.39x | 0.821% / 0.083% |
| 2024-12-02 11:15 | 2.53x | Full-bodied bearish | Impulse / continuation | 0.083% / -0.374% / -0.449% | True breakout | 70.3% | 16.2% | 13.5% | 0.94x | 0.640% / 0.166% |
| 2024-12-03 10:00 | 14.10x | Small-body bearish | Impulse / continuation | -0.067% / -0.209% / -0.962% | True breakout | 38.2% | 31.6% | 30.3% | 6.45x | 1.045% / 0.017% |
| 2024-12-03 10:15 | 6.12x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.142% / -0.343% / -1.138% | True breakout | 29.6% | 7.4% | 63.0% | 1.64x | 1.305% / 0.033% |
| 2024-12-03 10:30 | 5.04x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.201% / -0.754% / -0.570% | True breakout | 34.9% | 14.0% | 51.2% | 2.44x | 1.165% / 0.000% |
| 2024-12-03 10:45 | 4.44x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.554% / -0.798% / -0.504% | True breakout | 48.0% | 0.0% | 52.0% | 2.53x | 0.965% / 0.017% |
| 2024-12-03 11:00 | 4.84x | Full-bodied bearish | Impulse / continuation | -0.245% / 0.186% / 0.338% | True breakout | 83.3% | 3.8% | 12.8% | 3.42x | 0.414% / 0.371% |
| 2024-12-03 11:15 | 4.33x | Small-body bearish | Reversal | 0.432% / 0.296% / 0.449% | Liquidity sweep / reversal | 43.1% | 26.2% | 30.8% | 2.35x | 0.017% / 0.618% |
| 2024-12-03 11:30 | 3.52x | Full-bodied bullish | Flat / fading | -0.135% / 0.152% / 0.025% | Position building in range | 66.7% | 29.3% | 4.0% | 2.36x | 0.185% / 0.295% |
| 2024-12-04 10:00 | 10.61x | Small-body bullish | Reversal | -0.458% / -0.119% / 0.475% | Liquidity sweep / reversal | 40.0% | 38.7% | 21.3% | 5.77x | 0.610% / 0.687% |
| 2024-12-04 10:15 | 9.00x | Full-bodied bearish | Reversal | 0.341% / 0.545% / 1.150% | Liquidity sweep / reversal | 65.1% | 2.4% | 32.5% | 4.88x | 0.043% / 1.303% |
| 2024-12-04 10:30 | 5.23x | Full-bodied bullish | Impulse / continuation | 0.204% / 0.594% / 1.019% | True breakout | 85.1% | 4.3% | 10.6% | 2.12x | 1.256% / 0.102% |
| 2024-12-04 10:45 | 4.73x | Small-body bullish | Impulse / continuation | 0.390% / 0.601% / 0.796% | True breakout | 50.0% | 28.0% | 22.0% | 2.06x | 1.050% / 0.110% |
| 2024-12-04 11:00 | 4.83x | Full-bodied bullish | Impulse / continuation | 0.211% / 0.422% / 0.017% | True breakout | 61.3% | 21.3% | 17.3% | 2.82x | 0.658% / 0.152% |
| 2024-12-04 11:15 | 3.53x | Small-body bullish | Impulse / continuation | 0.210% / 0.194% / -0.084% | True breakout | 41.0% | 29.5% | 29.5% | 1.97x | 0.446% / 0.227% |
| 2024-12-04 11:30 | 3.58x | Bearish pin-bar / upper rejection | Reversal | -0.017% / -0.403% / -0.479% | Liquidity sweep / reversal | 48.1% | 51.9% | 0.0% | 1.57x | 0.076% / 0.555% |
| 2024-12-04 18:15 | 3.49x | Full-bodied bearish | Impulse / continuation | 0.310% / 0.310% / -1.662% | True breakout | 92.6% | 0.7% | 6.6% | 3.36x | 2.187% / 0.379% |
| 2024-12-04 19:00 | 3.26x | Small-body bearish | Flat / fading | -0.131% / 0.245% / 0.079% | Position building in range | 50.0% | 16.7% | 33.3% | 4.59x | 0.603% / 0.385% |
| 2024-12-05 10:00 | 6.29x | Full-bodied bullish | Impulse / continuation | -0.268% / 0.078% / 0.398% | True breakout | 82.2% | 3.7% | 14.0% | 5.41x | 0.476% / 0.536% |
| 2024-12-05 10:15 | 4.78x | Small-body bearish | Reversal | 0.347% / 0.225% / 0.780% | Liquidity sweep / reversal | 34.8% | 30.3% | 34.8% | 3.59x | 0.061% / 0.928% |
| 2024-12-05 10:30 | 3.65x | Small-body bullish | Impulse / continuation | -0.121% / 0.320% / 0.086% | True breakout | 55.7% | 32.9% | 11.4% | 2.34x | 0.579% / 0.320% |
| 2024-12-06 10:00 | 4.02x | Full-bodied bearish | Impulse / continuation | -0.279% / 0.271% / 0.262% | True breakout | 75.3% | 14.1% | 10.6% | 3.55x | 0.423% / 0.660% |
| 2024-12-06 10:15 | 3.15x | Bearish pin-bar / upper rejection | Reversal | 0.552% / 0.815% / 0.365% | Liquidity sweep / reversal | 47.1% | 51.5% | 1.5% | 2.42x | 0.144% / 0.942% |
| 2024-12-06 10:30 | 4.12x | Full-bodied bullish | Flat / fading | 0.262% / -0.008% / -0.051% | Weak move without breakout | 66.3% | 16.3% | 17.3% | 3.14x | 0.388% / 0.363% |
| 2024-12-06 10:45 | 3.64x | Full-bodied bullish | Reversal | -0.269% / -0.446% / -0.648% | Liquidity sweep / reversal | 67.4% | 32.6% | 0.0% | 1.32x | 0.025% / 0.766% |
| 2024-12-06 11:00 | 2.53x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.177% / -0.042% / -0.430% | True breakout | 54.1% | 3.3% | 42.6% | 1.73x | 0.616% / 0.025% |
| 2024-12-06 15:00 | 2.40x | Small-body bullish | Reversal | -0.344% / -0.176% / -0.647% | Liquidity sweep / reversal | 56.5% | 36.3% | 7.3% | 2.25x | 0.151% / 0.798% |
| 2024-12-09 10:00 | 7.83x | Full-bodied bearish | Flat / fading | 0.220% / 0.211% / 0.321% | Position building in range | 90.4% | 1.2% | 8.4% | 2.27x | 0.000% / 0.490% |
| 2024-12-09 10:15 | 4.35x | Bearish pin-bar / upper rejection | Flat / fading | -0.008% / 0.202% / -0.084% | Weak move without breakout | 52.0% | 48.0% | 0.0% | 1.19x | 0.270% / 0.160% |
| 2024-12-09 16:15 | 2.67x | Full-bodied bullish | Impulse / continuation | 0.259% / 0.493% / 0.167% | True breakout | 81.8% | 9.1% | 9.1% | 2.88x | 0.635% / 0.150% |
| 2024-12-09 16:45 | 2.78x | Small-body bullish | Reversal | -0.474% / -0.324% / -0.233% | Liquidity sweep / reversal | 52.0% | 24.0% | 24.0% | 2.10x | 0.141% / 0.507% |
| 2024-12-09 17:00 | 2.47x | Full-bodied bearish | Flat / fading | 0.150% / 0.150% / 0.367% | Position building in range | 73.1% | 21.8% | 5.1% | 3.02x | 0.033% / 0.476% |
| 2024-12-10 10:00 | 12.19x | Full-bodied bearish | Impulse / continuation | -0.385% / -0.285% / -0.645% | True breakout | 74.6% | 5.1% | 20.3% | 5.13x | 0.846% / 0.050% |
| 2024-12-10 10:15 | 10.63x | Full-bodied bearish | Impulse / continuation | 0.101% / -0.227% / -0.134% | True breakout | 66.7% | 8.7% | 24.6% | 4.71x | 0.462% / 0.202% |
| 2024-12-10 10:30 | 3.25x | Small-body bullish | Reversal | -0.327% / -0.361% / -0.327% | Liquidity sweep / reversal | 36.7% | 26.7% | 36.7% | 1.57x | 0.101% / 0.563% |
| 2024-12-10 10:45 | 3.27x | Full-bodied bearish | Impulse / continuation | -0.034% / 0.093% / -0.135% | True breakout | 62.9% | 19.4% | 17.7% | 3.07x | 0.320% / 0.278% |
| 2024-12-10 11:00 | 2.94x | Bullish pin-bar / lower rejection | Reversal | 0.126% / 0.034% / -0.118% | Liquidity sweep / reversal | 10.0% | 30.0% | 60.0% | 1.69x | 0.287% / 0.312% |
| 2024-12-10 12:15 | 2.56x | Full-bodied bearish | Flat / fading | 0.204% / 0.263% / 0.204% | Weak move without breakout | 79.4% | 2.1% | 18.6% | 3.11x | 0.246% / 0.442% |
| 2024-12-11 10:00 | 17.00x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.085% / -0.103% / -0.197% | True breakout | 48.4% | 0.0% | 51.6% | 6.29x | 0.470% / 0.180% |
| 2024-12-11 10:15 | 5.79x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.017% / -0.231% / -0.043% | True breakout | 32.3% | 67.7% | 0.0% | 2.26x | 0.385% / 0.103% |
| 2024-12-11 10:30 | 2.64x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.214% / -0.094% / -0.009% | True breakout | 9.1% | 54.5% | 36.4% | 1.41x | 0.368% / 0.094% |
| 2024-12-11 10:45 | 3.43x | Full-bodied bearish | Impulse / continuation | 0.120% / 0.189% / 0.111% | True breakout | 78.1% | 21.9% | 0.0% | 1.94x | 0.154% / 0.309% |
| 2024-12-11 11:00 | 3.52x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.069% / 0.086% / 0.163% | True breakout | 27.0% | 13.5% | 59.5% | 2.03x | 0.214% / 0.120% |
| 2024-12-11 11:15 | 2.58x | Small-body bullish | Reversal | 0.017% / -0.077% / 0.411% | Liquidity sweep / reversal | 22.2% | 38.9% | 38.9% | 1.79x | 0.479% / 0.171% |
| 2024-12-11 19:00 | 3.38x | Small-body bullish | Flat / fading | -0.102% / -0.264% / -0.017% | Weak move without breakout | 57.6% | 12.1% | 30.3% | 3.72x | 0.196% / 0.358% |
| 2024-12-12 10:00 | 6.92x | Full-bodied bearish | Reversal | 0.077% / 0.307% / 0.461% | Liquidity sweep / reversal | 66.7% | 9.5% | 23.8% | 3.74x | 0.137% / 0.649% |
| 2024-12-12 10:15 | 3.74x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.230% / 0.486% / 0.486% | True breakout | 31.0% | 13.8% | 55.2% | 1.48x | 0.571% / 0.051% |
| 2024-12-12 10:30 | 4.17x | Full-bodied bullish | Impulse / continuation | 0.255% / 0.153% / 0.136% | True breakout | 74.4% | 15.4% | 10.3% | 1.90x | 0.340% / 0.017% |
| 2024-12-12 10:45 | 4.93x | Full-bodied bullish | Flat / fading | -0.102% / 0.000% / -0.195% | Position building in range | 69.0% | 23.8% | 7.1% | 1.90x | 0.076% / 0.246% |
| 2024-12-12 11:00 | 3.46x | Small-body bearish | Flat / fading | 0.102% / -0.017% / -0.170% | Weak move without breakout | 48.0% | 16.0% | 36.0% | 1.02x | 0.263% / 0.178% |
| 2024-12-13 10:00 | 8.41x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.000% / 0.009% / -0.165% | True breakout | 48.8% | 7.0% | 44.2% | 3.29x | 0.147% / 0.277% |
| 2024-12-13 10:15 | 4.00x | Bullish pin-bar / lower rejection | Reversal | 0.009% / -0.087% / -0.520% | Liquidity sweep / reversal | 2.9% | 8.6% | 88.6% | 2.28x | 0.147% / 0.572% |
| 2024-12-13 10:30 | 4.72x | Bullish pin-bar / lower rejection | Reversal | -0.095% / -0.173% / -0.719% | Liquidity sweep / reversal | 2.1% | 33.3% | 64.6% | 2.79x | 0.017% / 0.805% |
| 2024-12-13 10:45 | 2.80x | Full-bodied bearish | Impulse / continuation | -0.078% / -0.433% / -0.520% | True breakout | 65.0% | 0.0% | 35.0% | 1.00x | 0.711% / 0.113% |
| 2024-12-13 11:30 | 4.05x | Full-bodied bearish | Impulse / continuation | 0.105% / 0.113% / -0.279% | True breakout | 61.5% | 12.8% | 25.6% | 1.56x | 0.314% / 0.323% |
| 2024-12-13 13:30 | 2.57x | Bearish pin-bar / upper rejection | Reversal | -0.113% / -0.156% / -0.104% | Liquidity sweep / reversal | 53.8% | 43.6% | 2.6% | 1.18x | 0.139% / 0.270% |
| 2024-12-16 10:00 | 13.93x | Small-body bearish | Impulse / continuation | -0.105% / -0.359% / -0.640% | True breakout | 40.0% | 30.0% | 30.0% | 3.27x | 0.710% / 0.105% |
| 2024-12-16 10:15 | 5.27x | Small-body bearish | Impulse / continuation | -0.254% / -0.105% / -0.500% | True breakout | 36.4% | 36.4% | 27.3% | 2.35x | 0.667% / 0.079% |
| 2024-12-16 10:30 | 5.49x | Full-bodied bearish | Impulse / continuation | 0.150% / -0.282% / -0.695% | True breakout | 61.4% | 25.0% | 13.6% | 2.77x | 0.809% / 0.167% |
| 2024-12-16 10:45 | 3.35x | Full-bodied bullish | Reversal | -0.430% / -0.395% / -0.729% | Liquidity sweep / reversal | 77.3% | 9.1% | 13.6% | 1.19x | 0.009% / 0.975% |
| 2024-12-16 11:00 | 4.04x | Full-bodied bearish | Impulse / continuation | 0.035% / -0.415% / -0.388% | True breakout | 84.5% | 1.7% | 13.8% | 3.14x | 0.547% / 0.132% |
| 2024-12-16 11:15 | 2.83x | Bullish pin-bar / lower rejection | Reversal | -0.450% / -0.335% / -0.353% | Liquidity sweep / reversal | 13.3% | 36.7% | 50.0% | 1.41x | 0.035% / 0.582% |
| 2024-12-16 11:30 | 3.85x | Full-bodied bearish | Flat / fading | 0.115% / 0.027% / -0.062% | Weak move without breakout | 76.5% | 4.4% | 19.1% | 3.01x | 0.133% / 0.204% |
| 2024-12-16 13:45 | 3.10x | Full-bodied bearish | Flat / fading | 0.188% / -0.259% / -0.143% | Weak move without breakout | 77.4% | 0.0% | 22.6% | 3.61x | 0.483% / 0.304% |
| 2024-12-17 10:00 | 6.23x | Full-bodied bullish | Flat / fading | 0.063% / 0.027% / -0.036% | Weak move without breakout | 69.0% | 30.1% | 0.9% | 3.24x | 0.534% / 0.253% |
| 2024-12-17 10:15 | 3.29x | Bearish pin-bar / upper rejection | Reversal | -0.036% / 0.262% / -0.597% | Liquidity sweep / reversal | 8.3% | 72.2% | 19.4% | 1.77x | 0.335% / 0.724% |
| 2024-12-18 10:00 | 12.19x | Full-bodied bullish | Reversal | -0.260% / -0.054% / -0.529% | Liquidity sweep / reversal | 73.0% | 27.0% | 0.0% | 2.73x | 0.036% / 0.691% |
| 2024-12-18 10:15 | 3.84x | Full-bodied bearish | Impulse / continuation | 0.207% / 0.045% / -0.180% | True breakout | 75.0% | 11.1% | 13.9% | 2.31x | 0.432% / 0.297% |
| 2024-12-18 10:30 | 3.40x | Full-bodied bullish | Reversal | -0.162% / -0.476% / -0.305% | Liquidity sweep / reversal | 79.3% | 3.4% | 17.2% | 1.64x | 0.090% / 0.637% |
| 2024-12-18 11:00 | 3.69x | Small-body bearish | Flat / fading | 0.090% / 0.171% / -0.235% | Weak move without breakout | 57.1% | 14.3% | 28.6% | 3.23x | 0.289% / 0.262% |
| 2024-12-18 19:00 | 5.01x | Bearish pin-bar / upper rejection | Reversal | -0.382% / -0.133% / 0.124% | Liquidity sweep / reversal | 30.6% | 48.2% | 21.2% | 3.40x | 0.436% / 0.542% |
| 2024-12-19 10:00 | 2.59x | Full-bodied bearish | Impulse / continuation | -0.266% / -0.115% / -0.071% | True breakout | 67.4% | 21.7% | 10.9% | 2.08x | 0.408% / 0.089% |
| 2024-12-19 11:15 | 4.70x | Full-bodied bullish | Impulse / continuation | 0.106% / 0.520% / 0.238% | True breakout | 75.5% | 14.5% | 10.0% | 4.10x | 0.811% / 0.203% |
| 2024-12-19 11:30 | 2.97x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.414% / 0.581% / -0.026% | True breakout | 21.6% | 31.4% | 47.1% | 1.56x | 0.705% / 0.123% |
| 2024-12-19 11:45 | 3.45x | Full-bodied bullish | Reversal | 0.167% / -0.281% / -0.140% | Liquidity sweep / reversal | 68.1% | 11.6% | 20.3% | 2.01x | 0.289% / 0.447% |
| 2024-12-19 12:00 | 2.91x | Small-body bullish | Reversal | -0.447% / -0.604% / -0.018% | Liquidity sweep / reversal | 42.2% | 31.1% | 26.7% | 1.23x | 0.088% / 0.613% |
| 2024-12-19 15:00 | 1.93x | Full-bodied bullish | Flat / fading | -0.079% / 0.096% / -0.079% | Weak move without breakout | 69.9% | 28.8% | 1.4% | 1.50x | 0.367% / 0.157% |
| 2024-12-20 10:00 | 7.45x | Bearish pin-bar / upper rejection | Reversal | -0.229% / -0.132% / 0.062% | Liquidity sweep / reversal | 13.3% | 44.4% | 42.2% | 3.21x | 0.062% / 0.422% |
| 2024-12-20 10:15 | 4.78x | Small-body bearish | Reversal | 0.097% / 0.026% / 0.273% | Liquidity sweep / reversal | 58.7% | 8.7% | 32.6% | 2.86x | 0.194% / 0.397% |
| 2024-12-20 10:30 | 4.20x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.070% / 0.194% / 0.220% | True breakout | 29.5% | 25.0% | 45.5% | 2.64x | 0.300% / 0.194% |
| 2024-12-20 11:15 | 3.53x | Bearish pin-bar / upper rejection | Reversal | 0.044% / -0.123% / 0.088% | Liquidity sweep / reversal | 13.0% | 47.8% | 39.1% | 1.12x | 0.220% / 0.264% |
| 2024-12-20 13:30 | 16.16x | Bearish pin-bar / upper rejection | Flat / fading | -0.024% / 0.675% / 0.610% | Position building in range | 54.3% | 45.7% | 0.0% | 37.73x | 1.292% / 0.439% |
| 2024-12-20 13:45 | 4.08x | Bearish pin-bar / upper rejection | Reversal | 0.699% / 0.650% / 0.447% | Liquidity sweep / reversal | 0.6% | 89.5% | 9.9% | 1.18x | 0.415% / 1.317% |
| 2024-12-20 14:00 | 2.98x | Small-body bullish | Flat / fading | -0.048% / -0.065% / 0.589% | Weak move without breakout | 46.7% | 25.5% | 27.7% | 1.19x | 0.630% / 0.694% |
| 2024-12-20 15:15 | 3.11x | Full-bodied bullish | Flat / fading | 0.252% / -0.165% / 0.668% | Weak move without breakout | 94.9% | 3.3% | 1.8% | 1.43x | 0.794% / 0.527% |
| 2024-12-23 10:00 | 5.23x | Bearish pin-bar / upper rejection | Reversal | 0.911% / 0.764% / 1.375% | Liquidity sweep / reversal | 37.9% | 46.4% | 15.7% | 3.15x | 0.687% / 1.514% |
| 2024-12-23 10:15 | 5.37x | Small-body bullish | Impulse / continuation | -0.145% / -0.084% / 0.605% | True breakout | 50.6% | 10.4% | 39.0% | 3.99x | 1.010% / 0.474% |
| 2024-12-23 10:30 | 2.96x | Bullish pin-bar / lower rejection | Reversal | 0.061% / 0.605% / 0.253% | Liquidity sweep / reversal | 31.4% | 11.4% | 57.1% | 0.97x | 0.330% / 1.157% |
| 2024-12-23 10:45 | 3.16x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.544% / 0.689% / 0.383% | True breakout | 13.0% | 26.1% | 60.9% | 0.92x | 1.095% / 0.008% |
| 2024-12-23 11:00 | 4.52x | Full-bodied bullish | Flat / fading | 0.145% / -0.350% / -0.442% | Weak move without breakout | 80.0% | 20.0% | 0.0% | 1.18x | 0.548% / 0.480% |
| 2024-12-23 11:15 | 4.17x | Bearish pin-bar / upper rejection | Reversal | -0.494% / -0.304% / -0.479% | Liquidity sweep / reversal | 15.2% | 42.4% | 42.4% | 1.53x | 0.023% / 0.928% |
| 2024-12-24 10:00 | 9.69x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.177% / -0.684% | True breakout | 85.0% | 10.0% | 5.0% | 6.57x | 0.722% / 0.161% |
| 2024-12-24 10:15 | 8.52x | Doji / lower rejection | Impulse / continuation | -0.177% / -0.161% / 0.046% | True breakout | 0.0% | 32.8% | 67.2% | 3.02x | 0.730% / 0.730% |
| 2024-12-24 10:30 | 3.78x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.015% / -0.508% / 0.285% | False breakout | 40.7% | 40.7% | 18.5% | 2.30x | 0.554% / 0.408% |
| 2024-12-24 10:45 | 3.89x | Bullish pin-bar / lower rejection | Reversal | -0.523% / 0.208% / 0.285% | Liquidity sweep / reversal | 3.6% | 29.1% | 67.3% | 2.09x | 0.392% / 0.569% |
| 2024-12-24 11:00 | 3.25x | Full-bodied bearish | Reversal | 0.735% / 0.797% / 1.021% | Liquidity sweep / reversal | 79.5% | 14.5% | 6.0% | 2.81x | 0.046% / 1.106% |
| 2024-12-24 11:15 | 3.94x | Full-bodied bullish | Impulse / continuation | 0.061% / 0.077% / 0.729% | True breakout | 77.8% | 13.7% | 8.5% | 3.38x | 0.883% / 0.154% |
| 2024-12-24 11:30 | 3.17x | Small-body bullish | Impulse / continuation | 0.015% / 0.222% / 0.399% | True breakout | 20.0% | 40.0% | 40.0% | 0.97x | 0.821% / 0.215% |
| 2024-12-24 12:15 | 2.51x | Full-bodied bullish | Reversal | -0.267% / -0.320% / -0.579% | Liquidity sweep / reversal | 72.0% | 24.4% | 3.7% | 1.72x | 0.145% / 0.732% |
| 2024-12-25 10:00 | 9.74x | Small-body bullish | Impulse / continuation | 0.140% / 0.171% / -0.023% | True breakout | 47.0% | 22.0% | 31.0% | 6.09x | 0.521% / 0.257% |
| 2024-12-25 10:15 | 9.86x | Bearish pin-bar / upper rejection | Reversal | 0.031% / -0.280% / 0.287% | Liquidity sweep / reversal | 25.4% | 69.0% | 5.6% | 3.21x | 0.303% / 0.396% |
| 2024-12-25 10:30 | 3.89x | Bullish pin-bar / lower rejection | Reversal | -0.311% / -0.194% / 0.233% | Liquidity sweep / reversal | 21.2% | 27.3% | 51.5% | 1.25x | 0.349% / 0.427% |
| 2024-12-25 10:45 | 3.98x | Full-bodied bearish | Reversal | 0.117% / 0.569% / 0.444% | Liquidity sweep / reversal | 67.8% | 15.3% | 16.9% | 2.13x | 0.117% / 0.662% |
| 2024-12-25 11:00 | 2.92x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.451% / 0.428% / 0.739% | True breakout | 40.0% | 14.3% | 45.7% | 1.16x | 0.902% / 0.101% |
| 2024-12-25 11:15 | 3.20x | Full-bodied bullish | Impulse / continuation | -0.023% / -0.124% / 0.589% | True breakout | 80.8% | 2.7% | 16.4% | 2.39x | 0.813% / 0.240% |
| 2024-12-25 11:30 | 2.66x | Bullish pin-bar / lower rejection | Reversal | -0.101% / 0.310% / 0.689% | Liquidity sweep / reversal | 8.1% | 32.4% | 59.5% | 1.07x | 0.217% / 0.837% |
| 2024-12-25 12:00 | 3.11x | Full-bodied bullish | Impulse / continuation | 0.301% / 0.378% / 0.201% | True breakout | 69.2% | 26.9% | 3.8% | 2.06x | 0.525% / 0.085% |
| 2024-12-25 12:15 | 2.55x | Small-body bullish | Flat / fading | 0.077% / -0.046% / -0.162% | Position building in range | 48.1% | 36.7% | 15.2% | 1.84x | 0.192% / 0.370% |
| 2024-12-26 10:00 | 8.70x | Bearish pin-bar / upper rejection | Reversal | 0.356% / 0.553% / 0.507% | Liquidity sweep / reversal | 1.8% | 78.9% | 19.3% | 5.61x | 0.030% / 0.651% |
| 2024-12-26 10:15 | 4.68x | Full-bodied bullish | Impulse / continuation | 0.196% / 0.075% / -0.151% | True breakout | 86.5% | 1.9% | 11.5% | 1.96x | 0.294% / 0.219% |
| 2024-12-26 10:30 | 3.72x | Full-bodied bullish | Reversal | -0.120% / -0.045% / -0.783% | Liquidity sweep / reversal | 69.4% | 16.7% | 13.9% | 1.23x | 0.098% / 0.791% |
| 2024-12-26 11:15 | 2.64x | Full-bodied bearish | Impulse / continuation | -0.438% / -0.514% / -0.423% | True breakout | 78.8% | 3.8% | 17.3% | 1.67x | 0.748% / 0.015% |
| 2024-12-26 11:30 | 2.60x | Full-bodied bearish | Impulse / continuation | -0.076% / 0.076% / 0.213% | True breakout | 95.1% | 3.3% | 1.6% | 1.82x | 0.311% / 0.311% |
| 2024-12-27 10:00 | 4.56x | Small-body bullish | Flat / fading | 0.061% / 0.144% / 0.106% | Weak move without breakout | 47.9% | 27.4% | 24.7% | 2.63x | 0.296% / 0.197% |
| 2024-12-27 10:15 | 2.98x | Bullish pin-bar / lower rejection | Flat / fading | 0.083% / 0.099% / 0.023% | Weak move without breakout | 17.8% | 24.4% | 57.8% | 1.44x | 0.235% / 0.099% |
| 2024-12-27 16:30 | 3.00x | Full-bodied bearish | Impulse / continuation | -0.244% / -0.030% / -0.076% | True breakout | 60.7% | 1.8% | 37.5% | 3.32x | 0.403% / 0.061% |
| 2024-12-27 16:45 | 2.93x | Small-body bearish | Flat / fading | 0.214% / 0.145% / 0.137% | Weak move without breakout | 59.3% | 1.9% | 38.9% | 2.68x | 0.008% / 0.305% |
| 2024-12-28 10:00 | 8.07x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.189% / 0.325% / 0.530% | True breakout | 32.7% | 49.1% | 18.2% | 3.83x | 0.567% / 0.061% |
| 2024-12-28 10:15 | 2.58x | Full-bodied bullish | Impulse / continuation | 0.136% / 0.083% / 0.325% | True breakout | 75.8% | 0.0% | 24.2% | 1.91x | 0.408% / 0.076% |
| 2024-12-28 10:30 | 3.94x | Small-body bullish | Impulse / continuation | -0.053% / 0.204% / 0.204% | True breakout | 54.1% | 24.3% | 21.6% | 1.98x | 0.271% / 0.121% |
| 2024-12-28 11:00 | 2.80x | Full-bodied bullish | Impulse / continuation | -0.015% / 0.000% / 0.218% | True breakout | 85.4% | 12.2% | 2.4% | 2.00x | 0.241% / 0.128% |
| 2024-12-28 11:15 | 2.53x | Bullish pin-bar / lower rejection | Reversal | 0.015% / 0.135% / 0.181% | Liquidity sweep / reversal | 9.1% | 40.9% | 50.0% | 1.00x | 0.113% / 0.256% |
| 2024-12-28 11:45 | 3.06x | Small-body bullish | Reversal | 0.098% / 0.045% / -0.113% | Liquidity sweep / reversal | 57.1% | 25.0% | 17.9% | 1.22x | 0.120% / 0.225% |
| 2024-12-30 10:00 | 13.84x | Full-bodied bullish | Impulse / continuation | -0.331% / -0.169% / 0.015% | True breakout | 72.6% | 1.5% | 25.9% | 10.54x | 0.287% / 0.478% |
| 2024-12-30 10:15 | 6.33x | Small-body bearish | Reversal | 0.162% / 0.281% / 0.583% | Liquidity sweep / reversal | 43.3% | 37.5% | 19.2% | 3.21x | 0.066% / 0.583% |
| 2024-12-30 10:30 | 2.69x | Full-bodied bullish | Impulse / continuation | 0.118% / 0.184% / 0.568% | True breakout | 62.2% | 16.2% | 21.6% | 0.95x | 0.627% / 0.044% |
| 2025-01-03 10:00 | 8.75x | Small-body bearish | Impulse / continuation | 0.073% / 0.073% / -0.306% | True breakout | 50.4% | 38.5% | 11.1% | 5.79x | 0.474% / 0.357% |
| 2025-01-03 10:15 | 3.45x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.233% / -0.459% | Liquidity sweep / reversal | 18.2% | 70.9% | 10.9% | 1.97x | 0.131% / 0.553% |
| 2025-01-03 13:45 | 2.31x | Full-bodied bearish | Impulse / continuation | -0.519% / -0.437% / -0.319% | True breakout | 66.7% | 0.7% | 32.6% | 3.22x | 0.771% / 0.007% |
| 2025-01-06 10:00 | 13.53x | Bullish pin-bar / lower rejection | Reversal | 0.226% / 0.595% / 0.693% | Liquidity sweep / reversal | 33.3% | 1.3% | 65.3% | 3.65x | 0.000% / 0.746% |
| 2025-01-06 10:15 | 5.70x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.368% / 0.338% / 0.556% | True breakout | 46.9% | 53.1% | 0.0% | 2.55x | 0.669% / 0.000% |
| 2025-01-06 10:30 | 4.28x | Full-bodied bullish | Impulse / continuation | -0.030% / 0.097% / 0.457% | True breakout | 80.3% | 19.7% | 0.0% | 2.10x | 0.532% / 0.180% |
| 2025-01-06 10:45 | 3.11x | Bearish pin-bar / upper rejection | Reversal | 0.127% / 0.217% / 1.004% | Liquidity sweep / reversal | 8.3% | 58.3% | 33.3% | 1.10x | 0.150% / 1.064% |
| 2025-01-06 11:15 | 2.79x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.269% / 0.785% / 0.478% | True breakout | 40.5% | 40.5% | 18.9% | 1.04x | 0.845% / 0.022% |
| 2025-01-06 11:30 | 3.46x | Full-bodied bullish | Impulse / continuation | 0.514% / 0.335% / 0.194% | True breakout | 71.4% | 20.4% | 8.2% | 1.31x | 0.574% / 0.052% |
| 2025-01-06 11:45 | 2.90x | Full-bodied bullish | Reversal | -0.178% / -0.304% / -0.653% | Liquidity sweep / reversal | 84.5% | 9.5% | 6.0% | 2.07x | 0.022% / 0.668% |
| 2025-01-06 17:00 | 3.43x | Full-bodied bullish | Flat / fading | -0.103% / -0.015% / -0.037% | Weak move without breakout | 85.1% | 11.7% | 3.2% | 3.04x | 0.096% / 0.184% |
| 2025-01-08 10:00 | 10.81x | Full-bodied bullish | Impulse / continuation | 0.081% / 0.044% / 0.353% | True breakout | 63.0% | 25.0% | 12.0% | 6.74x | 0.353% / 0.037% |
| 2025-01-08 10:15 | 5.28x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.037% / 0.154% / 0.456% | True breakout | 28.2% | 59.0% | 12.8% | 2.05x | 0.507% / 0.118% |
| 2025-01-08 10:45 | 2.72x | Full-bodied bullish | Impulse / continuation | 0.117% / 0.301% / 0.198% | True breakout | 66.7% | 5.1% | 28.2% | 1.74x | 0.352% / 0.059% |
| 2025-01-08 11:00 | 2.82x | Full-bodied bullish | Impulse / continuation | 0.183% / 0.095% / -0.007% | True breakout | 66.7% | 0.0% | 33.3% | 0.99x | 0.235% / 0.066% |
| 2025-01-08 11:15 | 2.93x | Full-bodied bullish | Reversal | -0.088% / -0.102% / -0.139% | Liquidity sweep / reversal | 71.4% | 20.0% | 8.6% | 1.37x | 0.015% / 0.256% |
| 2025-01-09 10:00 | 32.79x | Full-bodied bullish | Flat / fading | -0.366% / -0.481% / -0.517% | Position building in range | 66.5% | 19.1% | 14.4% | 18.56x | 0.187% / 0.848% |
| 2025-01-09 10:15 | 7.42x | Small-body bearish | Impulse / continuation | -0.115% / -0.202% / -0.389% | True breakout | 59.8% | 28.7% | 11.5% | 2.99x | 0.483% / 0.166% |
| 2025-01-09 10:30 | 7.46x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.087% / -0.036% / -1.162% | True breakout | 18.8% | 17.5% | 63.7% | 2.34x | 1.263% / 0.282% |
| 2025-01-09 10:45 | 3.13x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.051% / -0.188% / -0.679% | True breakout | 15.4% | 50.0% | 34.6% | 2.01x | 1.178% / 0.369% |
| 2025-01-09 11:00 | 2.51x | Bearish pin-bar / upper rejection | Reversal | -0.238% / -1.127% / -1.148% | Liquidity sweep / reversal | 10.0% | 62.9% | 27.1% | 1.61x | 0.101% / 1.228% |
| 2025-01-09 11:30 | 2.67x | Full-bodied bearish | Impulse / continuation | 0.402% / -0.022% / -0.365% | True breakout | 87.9% | 2.1% | 9.9% | 2.85x | 0.920% / 0.475% |
| 2025-01-09 16:45 | 2.46x | Full-bodied bullish | Impulse / continuation | 0.196% / -0.232% / -0.421% | True breakout | 68.2% | 26.4% | 5.5% | 2.64x | 0.660% / 0.464% |
| 2025-01-10 10:00 | 14.66x | Bearish pin-bar / upper rejection | Reversal | 0.283% / 0.102% / -0.247% | Liquidity sweep / reversal | 3.2% | 71.8% | 25.0% | 4.42x | 0.261% / 0.443% |
| 2025-01-10 10:15 | 3.83x | Full-bodied bullish | Reversal | -0.181% / -0.326% / -0.608% | Liquidity sweep / reversal | 65.5% | 5.2% | 29.3% | 1.62x | 0.159% / 0.760% |
| 2025-01-10 10:30 | 3.88x | Small-body bearish | Impulse / continuation | -0.145% / -0.348% / -0.363% | True breakout | 43.9% | 38.6% | 17.5% | 1.48x | 0.580% / 0.109% |
| 2025-01-10 11:15 | 2.83x | Bullish pin-bar / lower rejection | Reversal | 0.066% / 0.175% / -0.058% | Liquidity sweep / reversal | 27.8% | 13.9% | 58.3% | 0.81x | 0.109% / 0.291% |
| 2025-01-10 13:00 | 3.54x | Full-bodied bullish | Impulse / continuation | -0.268% / 0.202% / 1.106% | True breakout | 93.3% | 3.7% | 3.0% | 2.56x | 1.410% / 0.333% |
| 2025-01-10 13:45 | 2.79x | Full-bodied bullish | Impulse / continuation | 0.344% / 0.438% / 0.086% | True breakout | 73.6% | 20.0% | 6.4% | 2.06x | 0.646% / 0.165% |
| 2025-01-10 14:00 | 2.56x | Small-body bullish | Impulse / continuation | 0.093% / -0.343% / 0.687% | True breakout | 42.5% | 37.2% | 20.4% | 1.98x | 0.729% / 0.386% |
| 2025-01-10 16:45 | 1.99x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.168% / 0.238% / 1.048% | True breakout | 55.6% | 42.6% | 1.9% | 1.30x | 1.236% / 0.251% |
| 2025-01-13 10:00 | 11.68x | Bearish pin-bar / upper rejection | Reversal | -0.840% / -0.753% / -0.652% | Liquidity sweep / reversal | 23.6% | 56.8% | 19.6% | 3.94x | 0.054% / 1.122% |
| 2025-01-13 10:15 | 5.25x | Full-bodied bearish | Flat / fading | 0.088% / 0.298% / 0.285% | Position building in range | 70.9% | 5.1% | 24.0% | 2.76x | 0.264% / 0.583% |
| 2025-01-13 10:30 | 2.83x | Bearish pin-bar / upper rejection | Flat / fading | 0.210% / 0.102% / 0.305% | Weak move without breakout | 11.0% | 52.3% | 36.7% | 1.48x | 0.494% / 0.210% |
| 2025-01-13 10:45 | 2.59x | Small-body bullish | Flat / fading | -0.108% / -0.014% / 0.034% | Weak move without breakout | 30.1% | 39.8% | 30.1% | 1.31x | 0.284% / 0.392% |
| 2025-01-14 10:00 | 4.24x | Small-body bullish | Impulse / continuation | 0.374% / 0.346% / -0.201% | True breakout | 46.9% | 20.7% | 32.4% | 2.39x | 0.797% / 0.215% |
| 2025-01-14 10:30 | 2.58x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.359% / -0.545% / 0.248% | False breakout | 3.5% | 72.1% | 24.4% | 1.38x | 0.718% / 0.338% |
| 2025-01-14 11:45 | 2.60x | Full-bodied bullish | Impulse / continuation | 0.397% / 0.294% / 0.616% | True breakout | 79.8% | 13.5% | 6.7% | 1.54x | 0.787% / 0.151% |
| 2025-01-14 12:00 | 3.01x | Bearish pin-bar / upper rejection | Flat / fading | -0.102% / 0.184% / 0.723% | Weak move without breakout | 43.5% | 43.5% | 13.0% | 1.79x | 0.879% / 0.545% |
| 2025-01-15 10:00 | 5.40x | Bearish pin-bar / upper rejection | Reversal | 0.225% / 0.314% / -0.130% | Liquidity sweep / reversal | 17.5% | 42.7% | 39.8% | 4.67x | 0.245% / 0.695% |
| 2025-01-15 10:30 | 3.41x | Bearish pin-bar / upper rejection | Reversal | -0.347% / -0.442% / -0.564% | Liquidity sweep / reversal | 12.8% | 59.6% | 27.7% | 3.25x | 0.041% / 0.700% |
| 2025-01-15 19:00 | 16.62x | Bearish pin-bar / upper rejection | Flat / fading | -0.155% / 0.088% / 0.155% | Position building in range | 59.9% | 40.1% | 0.0% | 8.60x | 0.485% / 0.357% |
| 2025-01-15 19:15 | 5.42x | Bearish pin-bar / upper rejection | Reversal | 0.243% / 0.297% / 0.216% | Liquidity sweep / reversal | 20.8% | 55.2% | 24.0% | 2.16x | 0.067% / 0.546% |
| 2025-01-16 10:00 | 4.19x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.609% / -0.649% / -0.268% | True breakout | 24.1% | 3.4% | 72.4% | 5.06x | 0.803% / 0.087% |
| 2025-01-16 12:00 | 4.01x | Bearish pin-bar / upper rejection | Flat / fading | -0.140% / 0.020% / -0.133% | Weak move without breakout | 46.7% | 52.2% | 1.1% | 1.86x | 0.194% / 0.340% |
| 2025-01-17 10:00 | 8.89x | Small-body bearish | Impulse -> reversal | -0.242% / 0.047% / 0.430% | False breakout | 43.3% | 32.8% | 23.9% | 3.11x | 0.577% / 0.463% |
| 2025-01-17 10:15 | 3.88x | Small-body bearish | Reversal | 0.289% / 0.296% / 0.942% | Liquidity sweep / reversal | 56.1% | 36.4% | 7.6% | 2.77x | 0.336% / 1.144% |
| 2025-01-17 10:30 | 5.89x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.007% / 0.382% / 0.624% | True breakout | 43.4% | 6.1% | 50.5% | 3.70x | 0.919% / 0.148% |
| 2025-01-17 10:45 | 3.44x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.376% / 0.644% / 0.577% | True breakout | 5.7% | 56.6% | 37.7% | 1.63x | 0.913% / 0.067% |
| 2025-01-17 11:00 | 3.10x | Full-bodied bullish | Impulse / continuation | 0.267% / 0.241% / 0.341% | True breakout | 78.9% | 7.0% | 14.1% | 2.07x | 0.535% / 0.020% |
| 2025-01-17 11:15 | 4.73x | Bearish pin-bar / upper rejection | Flat / fading | -0.027% / -0.067% / -0.253% | Weak move without breakout | 54.8% | 41.1% | 4.1% | 1.90x | 0.267% / 0.253% |
| 2025-01-17 16:30 | 3.30x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.433% / 0.600% / 0.753% | True breakout | 6.8% | 88.6% | 4.5% | 1.62x | 0.933% / 0.013% |
| 2025-01-17 16:45 | 3.34x | Full-bodied bullish | Impulse / continuation | 0.166% / 0.305% / 0.524% | True breakout | 68.7% | 30.2% | 1.0% | 3.52x | 0.544% / 0.066% |
| 2025-01-17 17:00 | 2.93x | Bearish pin-bar / upper rejection | Flat / fading | 0.139% / 0.152% / 0.278% | Weak move without breakout | 35.4% | 46.2% | 18.5% | 2.06x | 0.378% / 0.027% |
| 2025-01-20 10:00 | 10.28x | Bearish pin-bar / upper rejection | Reversal | 0.617% / 0.227% / -0.383% | Liquidity sweep / reversal | 32.1% | 56.4% | 11.5% | 3.49x | 0.630% / 0.754% |
| 2025-01-20 10:15 | 5.03x | Small-body bullish | Reversal | -0.387% / -0.439% / -0.956% | Liquidity sweep / reversal | 55.4% | 12.0% | 32.6% | 3.17x | 0.065% / 1.414% |
| 2025-01-20 11:00 | 2.57x | Full-bodied bearish | Flat / fading | 0.039% / -0.326% / -0.267% | Weak move without breakout | 66.9% | 3.1% | 29.9% | 1.93x | 0.424% / 0.261% |
| 2025-01-20 18:00 | 3.31x | Bullish pin-bar / lower rejection | Reversal | 0.173% / 0.047% / -0.100% | Liquidity sweep / reversal | 1.2% | 13.2% | 85.6% | 2.27x | 0.286% / 0.173% |
| 2025-01-20 21:15 | 3.24x | Bullish pin-bar / lower rejection | Flat / fading | 0.385% / 0.439% / 0.392% | Position building in range | 45.0% | 2.3% | 52.7% | 2.79x | 0.000% / 0.628% |
| 2025-01-21 10:00 | 3.27x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.087% / 0.161% / 0.649% | True breakout | 13.5% | 12.5% | 74.0% | 1.61x | 0.883% / 0.154% |
| 2025-01-21 17:30 | 3.63x | Full-bodied bullish | Impulse / continuation | -0.106% / 0.356% / 0.403% | True breakout | 76.9% | 6.7% | 16.3% | 1.82x | 0.891% / 0.284% |
| 2025-01-21 18:00 | 3.38x | Full-bodied bullish | Flat / fading | 0.506% / 0.046% / 0.039% | Weak move without breakout | 72.3% | 27.7% | 0.0% | 1.67x | 0.533% / 0.099% |
| 2025-01-22 10:00 | 7.78x | Full-bodied bearish | Flat / fading | 0.264% / 0.053% / 0.158% | Weak move without breakout | 61.4% | 20.5% | 18.2% | 5.50x | 0.264% / 0.522% |
| 2025-01-22 10:15 | 3.89x | Bearish pin-bar / upper rejection | Reversal | -0.211% / -0.349% / -0.217% | Liquidity sweep / reversal | 47.7% | 45.3% | 7.0% | 2.97x | 0.171% / 0.527% |
| 2025-01-22 10:30 | 2.61x | Small-body bearish | Flat / fading | -0.139% / 0.106% / 0.053% | Weak move without breakout | 42.1% | 34.2% | 23.7% | 2.33x | 0.317% / 0.284% |
| 2025-01-22 14:15 | 2.58x | Small-body bullish | Reversal | -0.105% / -0.216% / -0.439% | Liquidity sweep / reversal | 49.4% | 22.9% | 27.7% | 1.90x | 0.092% / 0.557% |
| 2025-01-22 19:00 | 9.37x | Small-body bearish | Impulse / continuation | -0.383% / -0.436% / -0.582% | True breakout | 56.1% | 10.0% | 34.0% | 9.76x | 1.203% / 0.357% |
| 2025-01-22 19:15 | 3.93x | Small-body bearish | Impulse / continuation | -0.053% / 0.080% / -0.285% | True breakout | 38.4% | 35.8% | 25.8% | 2.46x | 0.823% / 0.372% |
| 2025-01-23 10:00 | 3.59x | Bullish pin-bar / lower rejection | Reversal | 0.127% / 0.440% / 0.467% | Liquidity sweep / reversal | 40.4% | 19.1% | 40.4% | 3.56x | 0.187% / 0.627% |
| 2025-01-23 12:30 | 3.15x | Full-bodied bearish | Flat / fading | 0.274% / 0.428% / 0.441% | Position building in range | 85.4% | 9.8% | 4.9% | 2.06x | -0.007% / 0.522% |
| 2025-01-23 18:00 | 2.71x | Full-bodied bearish | Flat / fading | -0.114% / 0.100% / 0.134% | Weak move without breakout | 82.1% | 9.0% | 9.0% | 2.62x | 0.114% / 0.181% |
| 2025-01-23 19:45 | 3.34x | Small-body bullish | Flat / fading | 0.120% / 0.314% / 0.180% | Weak move without breakout | 58.2% | 27.0% | 14.8% | 3.47x | 0.454% / 0.013% |
| 2025-01-23 20:00 | 2.98x | Bearish pin-bar / upper rejection | Flat / fading | 0.193% / 0.027% / 0.013% | Position building in range | 24.3% | 71.4% | 4.3% | 1.73x | 0.227% / 0.113% |
| 2025-01-24 10:00 | 7.22x | Bearish pin-bar / upper rejection | Reversal | 0.199% / 0.053% / 0.298% | Liquidity sweep / reversal | 25.5% | 44.1% | 30.4% | 4.92x | 0.000% / 0.358% |
| 2025-01-24 11:15 | 2.80x | Small-body bullish | Flat / fading | -0.053% / -0.099% / -0.145% | Weak move without breakout | 56.6% | 22.6% | 20.8% | 1.63x | 0.112% / 0.237% |
| 2025-01-24 16:30 | 2.75x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.265% / -0.345% / -0.066% | True breakout | 59.3% | 0.0% | 40.7% | 3.60x | 0.630% / 0.146% |
| 2025-01-24 17:00 | 2.64x | Bullish pin-bar / lower rejection | Reversal | 0.133% / 0.280% / 0.433% | Liquidity sweep / reversal | 12.3% | 34.6% | 53.1% | 2.34x | 0.173% / 0.539% |
| 2025-01-27 09:15 | 2.91x | Full-bodied bearish | Impulse / continuation | 0.013% / -0.013% / -0.120% | True breakout | 71.4% | 0.0% | 28.6% | 3.42x | 0.386% / 0.133% |
| 2025-01-27 10:00 | 13.97x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / 0.007% / -0.140% | Weak move without breakout | 23.2% | 1.8% | 75.0% | 4.10x | 0.220% / 0.213% |
| 2025-01-27 10:15 | 4.38x | Bullish pin-bar / lower rejection | Reversal | 0.020% / 0.093% / -0.233% | Liquidity sweep / reversal | 8.8% | 0.0% | 91.2% | 2.06x | 0.333% / 0.227% |
| 2025-01-27 10:30 | 3.88x | Bearish pin-bar / upper rejection | Reversal | 0.073% / -0.147% / -0.160% | Liquidity sweep / reversal | 4.9% | 75.6% | 19.5% | 2.23x | 0.127% / 0.353% |
| 2025-01-27 11:15 | 2.69x | Small-body bearish | Impulse / continuation | 0.094% / -0.033% / -0.327% | True breakout | 32.7% | 36.7% | 30.6% | 2.14x | 0.428% / 0.200% |
| 2025-01-27 16:45 | 2.58x | Small-body bearish | Impulse / continuation | -0.074% / -0.188% / -0.188% | True breakout | 47.3% | 29.1% | 23.6% | 2.35x | 0.564% / 0.040% |
| 2025-01-27 17:00 | 3.84x | Bullish pin-bar / lower rejection | Flat / fading | -0.114% / -0.383% / -0.188% | Weak move without breakout | 17.5% | 0.0% | 82.5% | 2.64x | 0.491% / 0.114% |
| 2025-01-27 23:00 | 4.22x | Bullish pin-bar / lower rejection | Flat / fading | -0.130% / -0.048% / -0.178% | Position building in range | 32.2% | 3.5% | 64.3% | 2.95x | 0.288% / 0.151% |
| 2025-01-28 10:00 | 4.61x | Bearish pin-bar / upper rejection | Reversal | -0.075% / -0.055% / 0.184% | Liquidity sweep / reversal | 14.8% | 47.7% | 37.5% | 1.96x | 0.533% / 0.301% |
| 2025-01-28 12:00 | 2.42x | Full-bodied bearish | Reversal | 0.261% / 0.083% / 0.578% | Liquidity sweep / reversal | 71.8% | 12.9% | 15.3% | 1.32x | -0.014% / 0.750% |
| 2025-01-28 14:15 | 2.70x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.549% / 0.509% / 0.427% | True breakout | 33.7% | 66.3% | 0.0% | 1.84x | 0.909% / 0.000% |
| 2025-01-28 15:45 | 2.99x | Full-bodied bullish | Flat / fading | -0.134% / -0.174% / -0.067% | Weak move without breakout | 92.8% | 1.4% | 5.8% | 2.35x | 0.208% / 0.322% |
| 2025-01-28 16:00 | 2.42x | Bearish pin-bar / upper rejection | Reversal | -0.040% / 0.121% / 0.040% | Liquidity sweep / reversal | 25.4% | 50.7% | 23.9% | 1.03x | 0.188% / 0.255% |
| 2025-01-28 22:00 | 3.85x | Full-bodied bullish | Flat / fading | -0.219% / -0.060% / -0.166% | Weak move without breakout | 92.5% | 0.0% | 7.5% | 3.77x | 0.040% / 0.252% |
| 2025-01-29 10:00 | 5.25x | Bullish pin-bar / lower rejection | Reversal | 0.200% / 0.113% / 0.540% | Liquidity sweep / reversal | 3.7% | 46.9% | 49.4% | 2.67x | -0.007% / 0.567% |
| 2025-01-29 10:15 | 3.11x | Full-bodied bullish | Impulse / continuation | -0.087% / -0.080% / 0.666% | True breakout | 61.7% | 38.3% | 0.0% | 1.35x | 0.832% / 0.153% |
| 2025-01-29 11:00 | 4.71x | Full-bodied bullish | Impulse / continuation | 0.325% / 0.464% / 0.232% | True breakout | 92.4% | 6.1% | 1.5% | 1.75x | 0.531% / 0.053% |
| 2025-01-29 11:15 | 6.47x | Small-body bullish | Flat / fading | 0.139% / 0.119% / -0.093% | Weak move without breakout | 59.8% | 30.5% | 9.8% | 1.97x | 0.205% / 0.145% |
| 2025-01-29 12:30 | 3.46x | Full-bodied bullish | Flat / fading | -0.066% / 0.020% / -0.329% | Weak move without breakout | 88.9% | 2.0% | 9.1% | 2.19x | 0.178% / 0.375% |
| 2025-01-29 19:00 | 3.83x | Bullish pin-bar / lower rejection | Reversal | -0.283% / -0.751% / -0.211% | Liquidity sweep / reversal | 13.6% | 22.4% | 64.0% | 2.48x | 0.007% / 0.771% |
| 2025-01-30 09:00 | 4.65x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.013% / 0.264% / 0.237% | True breakout | 32.0% | 50.0% | 18.0% | 3.70x | 0.330% / 0.066% |
| 2025-01-30 09:15 | 2.52x | Bearish pin-bar / upper rejection | Reversal | 0.277% / 0.284% / 0.092% | Liquidity sweep / reversal | 21.4% | 50.0% | 28.6% | 1.68x | 0.053% / 0.343% |
| 2025-01-30 09:30 | 3.34x | Full-bodied bullish | Flat / fading | 0.007% / -0.026% / -0.224% | Weak move without breakout | 80.0% | 9.1% | 10.9% | 3.01x | 0.066% / 0.322% |
| 2025-01-30 10:00 | 11.72x | Bullish pin-bar / lower rejection | Reversal | -0.158% / -0.197% / 0.059% | Liquidity sweep / reversal | 10.2% | 13.6% | 76.3% | 2.63x | 0.329% / 0.224% |
| 2025-01-30 10:15 | 5.15x | Full-bodied bearish | Reversal | -0.040% / 0.072% / 0.112% | Liquidity sweep / reversal | 69.7% | 24.2% | 6.1% | 1.29x | 0.171% / 0.382% |
| 2025-01-30 11:00 | 5.36x | Bearish pin-bar / upper rejection | Reversal | -0.105% / -0.059% / -0.519% | Liquidity sweep / reversal | 46.8% | 53.2% | 0.0% | 1.70x | 0.007% / 0.559% |
| 2025-01-30 12:00 | 4.38x | Full-bodied bearish | Flat / fading | 0.040% / 0.126% / 0.059% | Position building in range | 83.8% | 7.4% | 8.8% | 2.00x | 0.033% / 0.278% |
| 2025-01-30 16:00 | 3.15x | Full-bodied bullish | Impulse / continuation | -0.033% / 0.085% / -0.059% | True breakout | 96.5% | 3.5% | 0.0% | 1.91x | 0.229% / 0.197% |
| 2025-01-31 09:15 | 4.48x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.150% / 0.235% / 0.267% | True breakout | 51.4% | 42.9% | 5.7% | 2.36x | 0.606% / 0.026% |
| 2025-01-31 09:30 | 5.00x | Small-body bullish | Impulse / continuation | 0.085% / 0.338% / 0.189% | True breakout | 52.3% | 38.6% | 9.1% | 2.61x | 0.455% / 0.085% |
| 2025-01-31 10:00 | 11.29x | Small-body bullish | Impulse / continuation | -0.220% / -0.149% / 0.130% | True breakout | 50.6% | 21.7% | 27.7% | 4.23x | 0.266% / 0.227% |
| 2025-01-31 10:15 | 5.34x | Full-bodied bearish | Reversal | 0.071% / 0.253% / 0.578% | Liquidity sweep / reversal | 73.9% | 26.1% | 0.0% | 1.87x | 0.006% / 0.669% |
| 2025-01-31 10:45 | 2.95x | Small-body bullish | Impulse -> reversal | 0.097% / 0.324% / -0.493% | False breakout | 58.0% | 40.0% | 2.0% | 1.88x | 0.415% / 0.518% |
| 2025-01-31 11:15 | 4.10x | Full-bodied bullish | Reversal | -0.039% / -0.814% / -0.491% | Liquidity sweep / reversal | 64.8% | 25.9% | 9.3% | 1.71x | 0.045% / 0.840% |
| 2025-01-31 11:45 | 4.45x | Full-bodied bearish | Flat / fading | 0.241% / 0.326% / 0.208% | Position building in range | 95.2% | 1.6% | 3.2% | 3.66x | 0.013% / 0.443% |
| 2025-01-31 15:45 | 2.67x | Full-bodied bearish | Impulse / continuation | 0.196% / 0.098% / -0.405% | True breakout | 81.1% | 1.1% | 17.8% | 2.46x | 0.496% / 0.235% |
| 2025-01-31 16:45 | 3.04x | Full-bodied bearish | Impulse / continuation | -0.033% / -0.256% / -0.249% | True breakout | 76.6% | 1.6% | 21.9% | 1.48x | 0.504% / 0.334% |
| 2025-02-03 07:00 | 5.31x | Full-bodied bearish | Flat / fading | 0.133% / 0.166% / 0.338% | Position building in range | 70.1% | 2.8% | 27.1% | 8.13x | -0.007% / 0.404% |
| 2025-02-03 10:00 | 5.96x | Small-body bullish | Reversal | -0.152% / -0.568% / -0.469% | Liquidity sweep / reversal | 35.1% | 31.2% | 33.8% | 2.09x | 0.013% / 0.806% |
| 2025-02-03 10:30 | 6.91x | Full-bodied bearish | Flat / fading | 0.206% / 0.100% / 0.013% | Position building in range | 63.3% | 0.0% | 36.7% | 2.33x | 0.159% / 0.319% |
| 2025-02-03 12:00 | 2.59x | Full-bodied bearish | Flat / fading | -0.093% / 0.007% / 0.354% | Weak move without breakout | 92.4% | 0.0% | 7.6% | 1.52x | 0.240% / 0.467% |
| 2025-02-03 20:45 | 4.38x | Full-bodied bullish | Impulse / continuation | 0.258% / 0.139% / 0.238% | True breakout | 79.7% | 20.3% | 0.0% | 3.09x | 0.410% / 0.000% |
| 2025-02-03 21:00 | 2.54x | Full-bodied bullish | Flat / fading | -0.119% / 0.033% / -0.026% | Position building in range | 61.3% | 37.1% | 1.6% | 2.11x | 0.112% / 0.204% |
| 2025-02-04 10:00 | 5.24x | Bullish pin-bar / lower rejection | Reversal | 0.066% / 0.223% / 0.079% | Liquidity sweep / reversal | 38.9% | 2.8% | 58.3% | 2.14x | 0.085% / 0.414% |
| 2025-02-04 10:15 | 2.82x | Small-body bullish | Impulse / continuation | 0.158% / 0.263% / 0.098% | True breakout | 35.5% | 25.8% | 38.7% | 1.69x | 0.348% / 0.092% |
| 2025-02-04 10:30 | 4.98x | Small-body bullish | Reversal | 0.105% / -0.144% / -0.223% | Liquidity sweep / reversal | 41.4% | 34.5% | 24.1% | 2.87x | 0.190% / 0.229% |
| 2025-02-04 10:45 | 3.66x | Small-body bullish | Reversal | -0.249% / -0.164% / -0.255% | Liquidity sweep / reversal | 42.1% | 34.2% | 23.7% | 1.79x | 0.039% / 0.386% |
| 2025-02-04 13:15 | 3.46x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.079% / -0.249% / -0.230% | True breakout | 1.9% | 51.9% | 46.3% | 1.83x | 0.610% / 0.066% |
| 2025-02-04 14:00 | 2.52x | Full-bodied bearish | Flat / fading | 0.303% / 0.198% / 0.066% | Position building in range | 79.3% | 0.0% | 20.7% | 1.84x | 0.040% / 0.303% |
| 2025-02-04 21:30 | 6.36x | Full-bodied bearish | Impulse / continuation | -0.160% / -0.127% / -0.127% | True breakout | 65.9% | 0.0% | 34.1% | 3.37x | 0.366% / 0.133% |
| 2025-02-04 21:45 | 3.75x | Bullish pin-bar / lower rejection | Flat / fading | 0.033% / 0.040% / -0.067% | Position building in range | 32.0% | 26.7% | 41.3% | 2.59x | 0.167% / 0.233% |
| 2025-02-05 10:00 | 5.15x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.179% / 0.100% / 0.020% | True breakout | 38.0% | 6.0% | 56.0% | 1.53x | 0.339% / 0.120% |
| 2025-02-05 10:15 | 4.05x | Small-body bullish | Reversal | -0.080% / 0.033% / -0.497% | Liquidity sweep / reversal | 38.8% | 32.8% | 28.4% | 1.89x | 0.159% / 0.524% |
| 2025-02-05 11:15 | 3.04x | Full-bodied bearish | Flat / fading | 0.207% / -0.013% / 0.187% | Weak move without breakout | 92.7% | 0.0% | 7.3% | 1.50x | 0.213% / 0.293% |
| 2025-02-05 12:00 | 2.56x | Bullish pin-bar / lower rejection | Reversal | 0.253% / 0.513% / 0.980% | Liquidity sweep / reversal | 18.2% | 31.8% | 50.0% | 0.99x | 0.007% / 1.320% |
| 2025-02-05 12:45 | 6.47x | Full-bodied bullish | Flat / fading | -0.270% / -0.158% / -0.257% | Position building in range | 91.7% | 8.3% | 0.0% | 2.51x | 0.040% / 0.421% |
| 2025-02-05 15:45 | 5.83x | Full-bodied bearish | Impulse / continuation | 0.153% / -0.193% / 0.113% | True breakout | 81.0% | 1.4% | 17.7% | 3.12x | 0.626% / 0.160% |
| 2025-02-05 19:00 | 3.64x | Bearish pin-bar / upper rejection | Flat / fading | 0.085% / 0.477% / 0.353% | Weak move without breakout | 45.7% | 54.3% | 0.0% | 2.09x | 0.660% / 0.157% |
| 2025-02-06 10:00 | 5.27x | Bullish pin-bar / lower rejection | Reversal | 0.168% / 0.719% / 1.289% | Liquidity sweep / reversal | 5.9% | 20.6% | 73.5% | 1.61x | 0.052% / 1.522% |
| 2025-02-06 10:15 | 7.40x | Full-bodied bullish | Impulse / continuation | 0.550% / 1.138% / 0.860% | True breakout | 60.5% | 20.9% | 18.6% | 1.95x | 1.351% / -0.013% |
| 2025-02-06 10:30 | 13.27x | Full-bodied bullish | Impulse / continuation | 0.585% / 0.566% / 0.193% | True breakout | 66.4% | 32.0% | 1.6% | 4.87x | 0.797% / 0.006% |
| 2025-02-06 10:45 | 8.24x | Full-bodied bullish | Reversal | -0.019% / -0.275% / -0.786% | Liquidity sweep / reversal | 72.8% | 26.4% | 0.8% | 3.91x | 0.109% / 1.189% |
| 2025-02-06 11:45 | 3.52x | Bullish pin-bar / lower rejection | Flat / fading | 0.213% / 0.193% / 0.084% | Weak move without breakout | 48.1% | 3.1% | 48.8% | 2.77x | 0.110% / 0.496% |
| 2025-02-06 17:00 | 2.90x | Bearish pin-bar / upper rejection | Flat / fading | -0.084% / -0.077% / -0.097% | Weak move without breakout | 36.9% | 46.2% | 16.9% | 1.10x | 0.200% / 0.303% |
| 2025-02-07 09:30 | 2.64x | Small-body bearish | Reversal | 0.122% / 0.039% / -0.071% | Liquidity sweep / reversal | 35.7% | 35.7% | 28.6% | 0.57x | 0.308% / 0.225% |
| 2025-02-07 10:00 | 8.07x | Small-body bearish | Impulse -> reversal | -0.077% / -0.109% / 0.128% | False breakout | 27.1% | 33.3% | 39.6% | 1.98x | 0.346% / 0.180% |
| 2025-02-07 10:15 | 5.02x | Bullish pin-bar / lower rejection | Reversal | -0.032% / 0.013% / 0.032% | Liquidity sweep / reversal | 23.6% | 0.0% | 76.4% | 2.09x | 0.180% / 0.257% |
| 2025-02-07 10:30 | 2.73x | Bearish pin-bar / upper rejection | Reversal | 0.045% / 0.238% / -0.032% | Liquidity sweep / reversal | 23.8% | 52.4% | 23.8% | 0.73x | 0.148% / 0.289% |
| 2025-02-07 11:00 | 3.92x | Small-body bullish | Reversal | -0.173% / -0.269% / -0.455% | Liquidity sweep / reversal | 60.0% | 17.8% | 22.2% | 1.58x | 0.013% / 0.590% |
| 2025-02-07 11:45 | 2.68x | Full-bodied bearish | Flat / fading | 0.032% / -0.129% / -0.129% | Weak move without breakout | 64.2% | 5.7% | 30.2% | 1.70x | 0.258% / 0.103% |
| 2025-02-07 20:15 | 2.83x | Full-bodied bullish | Flat / fading | -0.013% / -0.026% / 0.013% | Weak move without breakout | 79.2% | 12.5% | 8.3% | 1.67x | 0.077% / 0.071% |
| 2025-02-10 07:00 | 7.46x | Full-bodied bullish | Impulse / continuation | 0.077% / 0.236% / 0.440% | True breakout | 72.3% | 27.7% | 0.0% | 6.36x | 0.459% / 0.013% |
| 2025-02-10 07:30 | 2.65x | Small-body bullish | Flat / fading | -0.013% / 0.204% / 0.185% | Weak move without breakout | 58.3% | 39.6% | 2.1% | 2.26x | 0.223% / 0.064% |
| 2025-02-10 08:00 | 3.44x | Full-bodied bullish | Flat / fading | -0.108% / -0.019% / -0.140% | Weak move without breakout | 91.9% | 8.1% | 0.0% | 1.44x | 0.006% / 0.267% |
| 2025-02-10 09:45 | 3.90x | Full-bodied bullish | Impulse / continuation | -0.158% / 0.228% / 0.209% | True breakout | 63.1% | 27.7% | 9.2% | 1.95x | 0.425% / 0.298% |
| 2025-02-10 10:00 | 5.94x | Small-body bearish | Reversal | 0.387% / 0.451% / 0.095% | Liquidity sweep / reversal | 40.3% | 24.2% | 35.5% | 1.66x | 0.051% / 0.584% |
| 2025-02-10 10:15 | 3.71x | Full-bodied bullish | Flat / fading | 0.063% / -0.019% / -0.221% | Weak move without breakout | 76.5% | 14.8% | 8.6% | 1.97x | 0.196% / 0.386% |
| 2025-02-10 10:30 | 2.71x | Bearish pin-bar / upper rejection | Reversal | -0.082% / -0.354% / -0.436% | Liquidity sweep / reversal | 25.6% | 53.8% | 20.5% | 0.95x | 0.006% / 0.449% |
| 2025-02-10 16:45 | 4.28x | Bearish pin-bar / upper rejection | Flat / fading | 0.069% / 0.006% / -0.013% | Weak move without breakout | 19.8% | 64.2% | 16.0% | 2.83x | 0.239% / 0.132% |
| 2025-02-10 22:30 | 18.06x | Full-bodied bearish | Impulse / continuation | -0.242% / -0.446% / 0.166% | True breakout | 89.9% | 0.0% | 10.1% | 18.21x | 0.739% / 0.248% |
| 2025-02-10 22:45 | 8.22x | Bullish pin-bar / lower rejection | Reversal | -0.204% / 0.115% / 0.364% | Liquidity sweep / reversal | 29.1% | 25.4% | 45.5% | 5.53x | 0.498% / 0.492% |
| 2025-02-10 23:00 | 3.84x | Bearish pin-bar / upper rejection | Reversal | 0.320% / 0.614% / 0.928% | Liquidity sweep / reversal | 45.7% | 47.1% | 7.1% | 2.14x | 0.294% / 0.928% |
| 2025-02-12 07:00 | 7.09x | Full-bodied bullish | Impulse / continuation | 0.006% / 0.082% / 0.138% | True breakout | 65.8% | 2.6% | 31.6% | 3.06x | 0.163% / 0.082% |
| 2025-02-12 10:00 | 5.77x | Full-bodied bullish | Flat / fading | -0.138% / 0.075% / 0.013% | Weak move without breakout | 71.1% | 7.9% | 21.1% | 1.92x | 0.119% / 0.175% |
| 2025-02-12 10:30 | 5.20x | Full-bodied bullish | Flat / fading | 0.012% / -0.062% / -0.150% | Position building in range | 70.2% | 14.9% | 14.9% | 2.15x | 0.044% / 0.156% |
| 2025-02-12 14:30 | 2.38x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.182% / -0.157% | True breakout | 65.5% | 1.8% | 32.7% | 2.93x | 0.264% / 0.082% |
| 2025-02-12 18:00 | 4.48x | Full-bodied bearish | Impulse / continuation | 0.057% / -0.273% / 0.184% | True breakout | 63.2% | 25.6% | 11.2% | 3.13x | 0.952% / 0.273% |
| 2025-02-12 18:30 | 2.68x | Bullish pin-bar / lower rejection | Reversal | -0.064% / 0.458% / 1.088% | Liquidity sweep / reversal | 49.5% | 4.0% | 46.5% | 2.12x | 0.681% / 1.126% |
| 2025-02-12 19:00 | 4.50x | Full-bodied bullish | Impulse / continuation | 0.348% / 0.627% / 2.325% | True breakout | 69.4% | 7.3% | 23.3% | 3.81x | 3.079% / 0.158% |
| 2025-02-12 19:15 | 2.40x | Small-body bullish | Impulse / continuation | 0.278% / 0.915% / 3.889% | True breakout | 45.4% | 32.8% | 21.8% | 1.90x | 3.902% / 0.309% |
| 2025-02-12 19:45 | 2.69x | Full-bodied bullish | Impulse / continuation | 1.045% / 2.947% / 3.985% | True breakout | 81.6% | 0.0% | 18.4% | 1.71x | 6.350% / 0.050% |
| 2025-02-12 20:00 | 7.34x | Bearish pin-bar / upper rejection | Impulse / continuation | 1.882% / 3.281% / 3.176% | True breakout | 56.8% | 40.5% | 2.7% | 3.72x | 5.250% / 0.322% |
| 2025-02-12 20:15 | 3.69x | Full-bodied bullish | Impulse / continuation | 1.373% / 1.009% / 1.641% | True breakout | 84.9% | 0.6% | 14.5% | 3.63x | 3.306% / 0.231% |
| 2025-02-12 20:30 | 7.57x | Bearish pin-bar / upper rejection | Flat / fading | -0.360% / -0.102% / -0.138% | Position building in range | 38.5% | 54.6% | 6.9% | 4.80x | 0.977% / 1.241% |
| 2025-02-13 10:00 | 2.90x | Full-bodied bearish | Impulse / continuation | -0.173% / -0.938% / -0.848% | True breakout | 82.8% | 2.7% | 14.5% | 3.25x | 1.350% / 0.400% |
| 2025-02-13 10:30 | 2.62x | Full-bodied bearish | Reversal | 0.235% / 0.090% / 0.983% | Liquidity sweep / reversal | 64.8% | 0.0% | 35.2% | 1.08x | 0.151% / 0.983% |
| 2025-02-14 07:00 | 5.95x | Full-bodied bearish | Flat / fading | 0.095% / -0.255% / -0.207% | Position building in range | 70.2% | 0.0% | 29.8% | 25.94x | 0.255% / 0.207% |
| 2025-02-14 09:00 | 2.52x | Full-bodied bullish | Impulse / continuation | 0.494% / 0.224% / 0.418% | True breakout | 93.8% | 3.1% | 3.1% | 1.03x | 0.877% / 0.212% |
| 2025-02-14 09:15 | 5.20x | Small-body bullish | Flat / fading | -0.269% / -0.023% / -0.041% | Weak move without breakout | 51.2% | 39.6% | 9.1% | 1.25x | 0.141% / 0.703% |
| 2025-02-14 10:00 | 2.88x | Bullish pin-bar / lower rejection | Reversal | 0.035% / 0.006% / 0.897% | Liquidity sweep / reversal | 6.6% | 1.9% | 91.5% | 0.71x | 0.504% / 1.166% |
| 2025-02-14 10:45 | 3.59x | Full-bodied bullish | Flat / fading | 0.000% / -0.012% / 0.221% | Weak move without breakout | 89.9% | 3.0% | 7.1% | 2.27x | 0.349% / 0.256% |
| 2025-02-14 11:00 | 3.23x | Bearish pin-bar / upper rejection | Reversal | -0.012% / 0.302% / -0.244% | Liquidity sweep / reversal | 1.4% | 63.0% | 35.6% | 0.87x | 0.349% / 0.482% |
| 2025-02-14 13:30 | 8.29x | Small-body bearish | Flat / fading | -0.674% / -0.142% / -0.041% | Weak move without breakout | 58.4% | 10.0% | 31.6% | 6.08x | 1.354% / 0.467% |
| 2025-02-17 07:00 | 7.41x | Bearish pin-bar / upper rejection | Flat / fading | -0.193% / 0.000% / 0.041% | Position building in range | 40.7% | 40.7% | 18.5% | 3.03x | 0.175% / 0.193% |
| 2025-02-17 07:15 | 4.08x | Bearish pin-bar / upper rejection | Reversal | 0.193% / 0.129% / 0.287% | Liquidity sweep / reversal | 46.0% | 54.0% | 0.0% | 1.22x | 0.000% / 0.363% |
| 2025-02-17 10:00 | 4.22x | Bullish pin-bar / lower rejection | Reversal | -0.197% / -0.451% / -0.214% | Liquidity sweep / reversal | 15.5% | 21.4% | 63.1% | 1.18x | 0.139% / 0.671% |
| 2025-02-17 12:45 | 2.79x | Bearish pin-bar / upper rejection | Flat / fading | 0.184% / 0.328% / 0.098% | Weak move without breakout | 54.1% | 44.7% | 1.2% | 1.29x | 0.467% / 0.196% |
| 2025-02-17 18:00 | 3.11x | Full-bodied bullish | Impulse / continuation | 0.103% / -0.598% / -0.034% | True breakout | 83.3% | 16.7% | 0.0% | 2.64x | 0.559% / 0.969% |
| 2025-02-17 18:30 | 3.20x | Small-body bearish | Flat / fading | 0.258% / 0.568% / -0.103% | Weak move without breakout | 49.2% | 24.4% | 26.4% | 4.58x | 0.155% / 1.164% |
| 2025-02-18 10:15 | 4.79x | Full-bodied bearish | Flat / fading | 0.678% / 0.644% / 0.284% | Weak move without breakout | 70.8% | 3.5% | 25.7% | 2.54x | 0.081% / 0.841% |
| 2025-02-18 14:45 | 2.46x | Full-bodied bullish | Reversal | -1.603% / -1.867% / -1.798% | Liquidity sweep / reversal | 68.9% | 31.1% | 0.0% | 1.67x | 0.121% / 2.964% |
| 2025-02-18 15:00 | 3.31x | Full-bodied bearish | Impulse / continuation | -0.269% / -0.788% / 0.263% | True breakout | 84.7% | 7.4% | 8.0% | 4.36x | 1.384% / 0.298% |
| 2025-02-18 15:15 | 3.96x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.521% / 0.070% / 0.023% | False breakout | 26.0% | 28.9% | 45.1% | 1.82x | 1.118% / 0.568% |
| 2025-02-18 15:30 | 3.14x | Bullish pin-bar / lower rejection | Reversal | 0.594% / 1.059% / 1.153% | Liquidity sweep / reversal | 45.2% | 0.5% | 54.3% | 1.90x | 0.076% / 1.153% |
| 2025-02-19 07:00 | 2.55x | Bullish pin-bar / lower rejection | Flat / fading | 0.193% / 0.258% / 0.123% | Weak move without breakout | 5.2% | 27.3% | 67.5% | 1.24x | 0.269% / 0.240% |
| 2025-02-19 09:15 | 3.85x | Full-bodied bullish | Flat / fading | 0.192% / -0.006% / -0.321% | Weak move without breakout | 84.6% | 14.7% | 0.7% | 3.00x | 0.227% / 0.495% |
| 2025-02-19 10:00 | 3.38x | Small-body bearish | Impulse / continuation | -0.088% / -0.175% / -0.701% | True breakout | 41.5% | 24.5% | 34.0% | 1.83x | 0.847% / 0.058% |
| 2025-02-19 10:45 | 2.55x | Full-bodied bearish | Impulse / continuation | -0.182% / -0.123% / -0.370% | True breakout | 72.3% | 10.8% | 16.9% | 1.48x | 0.710% / 0.282% |
| 2025-02-19 11:15 | 3.38x | Bullish pin-bar / lower rejection | Reversal | -0.353% / -0.247% / -0.035% | Liquidity sweep / reversal | 17.2% | 6.3% | 76.6% | 1.05x | 0.159% / 0.588% |
| 2025-02-19 17:00 | 3.58x | Full-bodied bullish | Impulse / continuation | 0.105% / 0.707% / 0.584% | True breakout | 64.8% | 35.2% | 0.0% | 1.58x | 0.969% / 0.140% |
| 2025-02-19 17:30 | 4.28x | Full-bodied bullish | Flat / fading | 0.064% / -0.122% / -0.441% | Weak move without breakout | 79.8% | 0.0% | 20.2% | 2.70x | 0.261% / 0.696% |
| 2025-02-19 17:45 | 2.98x | Bearish pin-bar / upper rejection | Reversal | -0.185% / -0.498% / -0.504% | Liquidity sweep / reversal | 21.8% | 61.8% | 16.4% | 1.03x | 0.122% / 0.759% |
| 2025-02-19 19:00 | 3.76x | Bearish pin-bar / upper rejection | Reversal | 0.458% / 0.284% / 0.267% | Liquidity sweep / reversal | 18.6% | 52.4% | 29.0% | 2.68x | 0.075% / 0.534% |
| 2025-02-20 09:15 | 3.58x | Bearish pin-bar / upper rejection | Reversal | -0.259% / -0.109% / -0.242% | Liquidity sweep / reversal | 53.4% | 45.2% | 1.4% | 2.37x | 0.035% / 0.455% |
| 2025-02-20 09:30 | 3.36x | Full-bodied bearish | Flat / fading | 0.150% / 0.237% / 0.144% | Weak move without breakout | 82.1% | 0.0% | 17.9% | 1.61x | 0.196% / 0.295% |
| 2025-02-20 09:45 | 3.03x | Bullish pin-bar / lower rejection | Reversal | 0.087% / -0.133% / -0.317% | Liquidity sweep / reversal | 40.3% | 3.2% | 56.5% | 1.77x | 0.144% / 0.461% |
| 2025-02-20 10:00 | 4.45x | Bullish pin-bar / lower rejection | Reversal | -0.219% / -0.092% / -0.553% | Liquidity sweep / reversal | 33.3% | 18.5% | 48.1% | 1.50x | 0.052% / 0.743% |
| 2025-02-20 10:45 | 5.02x | Small-body bearish | Flat / fading | -0.150% / -0.133% / -0.121% | Weak move without breakout | 51.9% | 24.0% | 24.0% | 2.73x | 0.347% / 0.139% |
| 2025-02-20 15:45 | 4.67x | Bullish pin-bar / lower rejection | Reversal | 0.254% / 0.092% / 0.104% | Liquidity sweep / reversal | 27.9% | 21.4% | 50.6% | 3.65x | 0.139% / 0.283% |
| 2025-02-21 09:45 | 4.97x | Full-bodied bullish | Impulse / continuation | -0.081% / 0.081% / 0.203% | True breakout | 82.8% | 12.5% | 4.7% | 3.29x | 0.203% / 0.243% |
| 2025-02-21 10:00 | 4.59x | Bullish pin-bar / lower rejection | Reversal | 0.162% / 0.035% / 0.220% | Liquidity sweep / reversal | 30.4% | 8.7% | 60.9% | 2.04x | 0.093% / 0.354% |
| 2025-02-21 10:45 | 2.81x | Full-bodied bullish | Flat / fading | -0.064% / -0.104% / -0.110% | Weak move without breakout | 91.7% | 0.0% | 8.3% | 1.81x | 0.069% / 0.231% |
| 2025-02-21 11:00 | 2.61x | Bullish pin-bar / lower rejection | Flat / fading | -0.041% / -0.093% / 0.052% | Weak move without breakout | 21.3% | 27.7% | 51.1% | 1.65x | 0.168% / 0.093% |
| 2025-02-21 13:30 | 4.11x | Full-bodied bearish | Impulse / continuation | 0.058% / -0.443% / -0.653% | True breakout | 94.7% | 1.3% | 4.0% | 2.01x | 1.050% / 0.198% |
| 2025-02-21 13:45 | 3.05x | Bullish pin-bar / lower rejection | Reversal | -0.501% / -0.956% / -0.548% | Liquidity sweep / reversal | 17.0% | 26.4% | 56.6% | 1.34x | 0.140% / 1.108% |
| 2025-02-21 14:00 | 3.44x | Full-bodied bearish | Impulse / continuation | -0.457% / -0.211% / -0.205% | True breakout | 70.8% | 20.8% | 8.3% | 3.02x | 0.609% / 0.322% |
| 2025-02-21 14:15 | 6.74x | Bearish pin-bar / upper rejection | Flat / fading | 0.247% / 0.412% / 0.265% | Weak move without breakout | 52.1% | 40.3% | 7.6% | 3.09x | 0.153% / 0.506% |
| 2025-02-21 22:45 | 3.79x | Bullish pin-bar / lower rejection | Reversal | -0.088% / 0.088% / 0.134% | Liquidity sweep / reversal | 24.0% | 8.3% | 67.7% | 4.38x | 0.158% / 0.281% |
| 2025-02-24 10:00 | 6.64x | Bearish pin-bar / upper rejection | Reversal | -0.139% / -0.238% / -0.087% | Liquidity sweep / reversal | 50.8% | 41.0% | 8.2% | 2.89x | 0.046% / 0.302% |
| 2025-02-24 10:15 | 2.60x | Small-body bearish | Flat / fading | -0.099% / -0.163% / -0.012% | Weak move without breakout | 51.1% | 20.0% | 28.9% | 1.91x | 0.163% / 0.076% |
| 2025-02-24 10:30 | 3.37x | Small-body bearish | Reversal | -0.064% / 0.151% / -0.041% | Liquidity sweep / reversal | 53.1% | 12.5% | 34.4% | 1.43x | 0.070% / 0.175% |
| 2025-02-24 14:00 | 2.89x | Small-body bearish | Flat / fading | 0.111% / 0.146% / -0.117% | Weak move without breakout | 43.3% | 22.4% | 34.3% | 2.93x | 0.210% / 0.199% |
| 2025-02-24 17:00 | 2.49x | Small-body bullish | Flat / fading | -0.064% / 0.100% / 0.064% | Weak move without breakout | 40.0% | 34.3% | 25.7% | 1.79x | 0.228% / 0.076% |
| 2025-02-24 23:30 | 3.25x | Full-bodied bullish | Impulse / continuation | 0.058% / 0.180% / 0.133% | True breakout | 98.2% | 0.0% | 1.8% | 2.22x | 0.661% / 0.023% |
| 2025-02-25 07:00 | 5.44x | Bearish pin-bar / upper rejection | Reversal | -0.058% / 0.075% / 0.127% | Liquidity sweep / reversal | 2.0% | 80.6% | 17.3% | 3.85x | 0.162% / 0.133% |
| 2025-02-25 09:45 | 6.78x | Full-bodied bullish | Flat / fading | -0.040% / -0.373% / -0.281% | Position building in range | 79.3% | 19.8% | 0.8% | 3.89x | 0.034% / 0.465% |
| 2025-02-25 10:00 | 6.42x | Bullish pin-bar / lower rejection | Flat / fading | -0.333% / -0.327% / -0.167% | Weak move without breakout | 4.7% | 10.6% | 84.7% | 2.37x | 0.425% / 0.029% |
| 2025-02-26 07:00 | 5.37x | Small-body bullish | Flat / fading | 0.058% / 0.058% / 0.192% | Weak move without breakout | 29.8% | 34.0% | 36.2% | 5.39x | 0.273% / 0.000% |
| 2025-02-26 10:00 | 8.67x | Bullish pin-bar / lower rejection | Flat / fading | -0.006% / -0.006% / 0.035% | Weak move without breakout | 52.2% | 3.3% | 44.4% | 2.99x | 0.291% / 0.227% |
| 2025-02-26 10:30 | 3.26x | Bullish pin-bar / lower rejection | Reversal | 0.163% / 0.041% / -0.285% | Liquidity sweep / reversal | 3.6% | 12.5% | 83.9% | 1.60x | 0.233% / 0.419% |
| 2025-02-26 12:30 | 2.51x | Small-body bearish | Impulse / continuation | -0.099% / -0.351% / -1.322% | True breakout | 43.1% | 18.5% | 38.5% | 1.33x | 1.819% / 0.105% |
| 2025-02-26 13:15 | 5.04x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.899% / -0.699% / -0.529% | True breakout | 12.3% | 28.4% | 59.3% | 1.44x | 1.398% / 0.094% |
| 2025-02-26 13:30 | 6.22x | Full-bodied bearish | Flat / fading | 0.201% / 0.213% / 0.510% | Position building in range | 60.2% | 6.3% | 33.5% | 4.27x | 0.290% / 0.687% |
| 2025-02-26 16:15 | 2.47x | Full-bodied bearish | Reversal | 0.485% / 0.891% / 0.796% | Liquidity sweep / reversal | 66.3% | 1.1% | 32.6% | 0.94x | 0.263% / 1.113% |
| 2025-02-26 19:00 | 3.73x | Bullish pin-bar / lower rejection | Reversal | -0.813% / -0.281% / 0.018% | Liquidity sweep / reversal | 14.9% | 26.1% | 59.0% | 2.12x | 0.036% / 0.896% |
| 2025-02-27 07:30 | 3.65x | Small-body bearish | Impulse / continuation | -0.091% / 0.049% / -0.680% | True breakout | 59.8% | 10.9% | 29.3% | 3.63x | 0.995% / 0.310% |
| 2025-02-27 10:00 | 2.84x | Bearish pin-bar / upper rejection | Reversal | 0.515% / 0.509% / -0.503% | Liquidity sweep / reversal | 10.5% | 58.8% | 30.7% | 1.30x | 0.921% / 0.557% |
| 2025-02-27 15:30 | 2.78x | Full-bodied bullish | Flat / fading | -0.317% / 0.449% / 0.126% | Weak move without breakout | 77.9% | 15.4% | 6.7% | 1.24x | 0.539% / 0.527% |
| 2025-02-27 19:15 | 2.79x | Small-body bearish | Flat / fading | -0.055% / 0.261% / 0.067% | Position building in range | 57.2% | 5.7% | 37.1% | 3.76x | 0.255% / 0.436% |
| 2025-02-27 23:00 | 3.14x | Full-bodied bearish | Impulse / continuation | -0.270% / -0.405% / -0.772% | True breakout | 63.9% | 16.9% | 19.3% | 1.34x | 0.864% / 0.055% |
| 2025-02-27 23:15 | 3.14x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.135% / -0.393% / 0.123% | True breakout | 39.5% | 7.0% | 53.5% | 1.82x | 0.996% / 0.252% |
| 2025-02-28 07:00 | 2.70x | Small-body bullish | Flat / fading | 0.055% / 0.031% / 0.000% | Weak move without breakout | 52.2% | 10.3% | 37.4% | 3.24x | 0.491% / 0.104% |
| 2025-02-28 10:00 | 3.53x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.588% / -0.741% / -1.978% | True breakout | 19.5% | 57.6% | 22.9% | 1.68x | 2.247% / 0.110% |
| 2025-02-28 10:45 | 5.20x | Small-body bearish | Impulse / continuation | -0.689% / -0.627% / -0.161% | True breakout | 48.9% | 14.9% | 36.2% | 2.50x | 1.340% / 0.087% |
| 2025-02-28 11:00 | 3.83x | Full-bodied bearish | Flat / fading | 0.062% / 0.287% / 0.162% | Weak move without breakout | 65.7% | 8.3% | 26.0% | 2.01x | 0.656% / 0.537% |
| 2025-02-28 11:15 | 4.21x | Bullish pin-bar / lower rejection | Flat / fading | 0.225% / 0.468% / 0.231% | Weak move without breakout | 11.3% | 19.0% | 69.7% | 1.57x | 0.474% / 0.331% |
| 2025-02-28 19:45 | 2.74x | Full-bodied bullish | Impulse / continuation | -0.140% / -0.061% / 1.090% | True breakout | 63.7% | 9.6% | 26.8% | 2.32x | 1.669% / 0.706% |
| 2025-02-28 20:30 | 4.34x | Full-bodied bullish | Reversal | -0.096% / 0.150% / -1.077% | Liquidity sweep / reversal | 80.7% | 18.5% | 0.8% | 3.30x | 0.475% / 2.823% |
| 2025-02-28 21:15 | 4.80x | Full-bodied bearish | Flat / fading | 0.729% / 0.686% / 0.429% | Position building in range | 64.1% | 2.0% | 33.9% | 5.09x | 0.221% / 1.023% |
| 2025-03-02 10:45 | 6.94x | Bullish pin-bar / lower rejection | Flat / fading | 0.061% / -0.037% / -0.031% | Weak move without breakout | 52.9% | 4.3% | 42.9% | 3.08x | 0.244% / 0.092% |
| 2025-03-02 11:15 | 2.89x | Bullish pin-bar / lower rejection | Reversal | -0.043% / 0.006% / 0.220% | Liquidity sweep / reversal | 30.0% | 2.0% | 68.0% | 1.83x | 0.171% / 0.232% |
| 2025-03-03 07:00 | 12.18x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.326% / -0.467% | True breakout | 83.7% | 7.6% | 8.7% | 3.57x | 0.578% / 0.061% |
| 2025-03-03 07:15 | 7.11x | Bullish pin-bar / lower rejection | Reversal | -0.326% / -0.350% / -0.565% | Liquidity sweep / reversal | 8.6% | 17.2% | 74.1% | 1.91x | 0.000% / 0.793% |
| 2025-03-03 07:30 | 7.17x | Full-bodied bearish | Impulse / continuation | -0.025% / -0.142% / 0.018% | True breakout | 66.3% | 0.0% | 33.7% | 2.46x | 0.469% / 0.117% |
| 2025-03-03 08:00 | 3.89x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.099% / 0.161% / -0.253% | False breakout | 40.5% | 16.7% | 42.9% | 1.20x | 0.531% / 0.309% |
| 2025-03-03 08:15 | 4.13x | Bullish pin-bar / lower rejection | Reversal | 0.260% / 0.136% / 0.173% | Liquidity sweep / reversal | 25.8% | 14.5% | 59.7% | 1.67x | 0.433% / 0.408% |
| 2025-03-03 08:30 | 2.83x | Full-bodied bullish | Reversal | -0.123% / -0.413% / -0.382% | Liquidity sweep / reversal | 71.2% | 27.1% | 1.7% | 1.51x | 0.148% / 0.690% |
| 2025-03-03 09:00 | 4.20x | Bullish pin-bar / lower rejection | Reversal | 0.328% / 0.031% / -0.167% | Liquidity sweep / reversal | 44.8% | 12.4% | 42.9% | 2.37x | 0.285% / 0.328% |
| 2025-03-03 09:15 | 2.57x | Bullish pin-bar / lower rejection | Reversal | -0.296% / -0.222% / -0.574% | Liquidity sweep / reversal | 59.8% | 0.0% | 40.2% | 1.73x | -0.006% / 0.740% |
| 2025-03-03 10:00 | 3.84x | Small-body bearish | Flat / fading | -0.081% / -0.236% / 0.019% | Weak move without breakout | 48.3% | 30.3% | 21.3% | 1.44x | 0.372% / 0.186% |
| 2025-03-03 10:15 | 3.84x | Bullish pin-bar / lower rejection | Reversal | -0.155% / 0.050% / -0.329% | Liquidity sweep / reversal | 25.0% | 23.1% | 51.9% | 0.78x | 0.354% / 0.267% |
| 2025-03-03 10:30 | 2.47x | Small-body bearish | Reversal | 0.205% / 0.255% / -0.050% | Liquidity sweep / reversal | 52.1% | 12.5% | 35.4% | 0.70x | 0.385% / 0.423% |
| 2025-03-03 11:45 | 1.89x | Bullish pin-bar / lower rejection | Reversal | 0.093% / -0.167% / -0.298% | Liquidity sweep / reversal | 37.0% | 20.0% | 43.0% | 1.42x | 0.180% / 0.385% |
| 2025-03-03 13:15 | 2.32x | Small-body bearish | Flat / fading | 0.169% / 0.250% / 0.206% | Weak move without breakout | 53.3% | 19.6% | 27.2% | 1.45x | 0.363% / 0.444% |
| 2025-03-03 22:15 | 3.66x | Full-bodied bullish | Impulse / continuation | 0.541% / 0.528% / 0.043% | True breakout | 91.7% | 7.4% | 0.8% | 2.16x | 0.696% / 0.199% |
| 2025-03-03 22:30 | 4.56x | Full-bodied bullish | Reversal | -0.012% / -0.383% / -0.655% | Liquidity sweep / reversal | 73.1% | 0.0% | 26.9% | 1.84x | 0.155% / 0.742% |
| 2025-03-03 22:45 | 3.10x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.371% / -0.482% / -0.630% | True breakout | 1.4% | 36.6% | 62.0% | 1.07x | 0.729% / 0.012% |
| 2025-03-04 07:00 | 3.10x | Small-body bullish | Flat / fading | 0.012% / 0.092% / 0.290% | Weak move without breakout | 46.0% | 31.3% | 22.7% | 2.21x | 0.444% / 0.166% |
| 2025-03-04 10:00 | 3.24x | Bearish pin-bar / upper rejection | Impulse / continuation | 1.029% / 1.378% / 1.654% | True breakout | 13.1% | 48.6% | 38.3% | 1.98x | 1.954% / 0.018% |
| 2025-03-04 10:15 | 2.88x | Full-bodied bullish | Impulse / continuation | 0.346% / 0.521% / 0.594% | True breakout | 98.2% | 0.0% | 1.8% | 2.91x | 0.916% / 0.103% |
| 2025-03-04 10:30 | 4.74x | Small-body bullish | Impulse / continuation | 0.175% / 0.272% / 0.592% | True breakout | 55.7% | 30.2% | 14.2% | 1.61x | 0.737% / 0.030% |
| 2025-03-04 19:00 | 10.59x | Small-body bullish | Flat / fading | -0.653% / -0.441% / -0.465% | Position building in range | 52.1% | 34.7% | 13.2% | 5.92x | 0.041% / 0.677% |
| 2025-03-04 19:15 | 5.48x | Full-bodied bearish | Flat / fading | 0.213% / 0.533% / 0.409% | Weak move without breakout | 92.5% | 5.8% | 1.7% | 1.86x | 0.024% / 0.563% |
| 2025-03-05 07:00 | 4.69x | Bullish pin-bar / lower rejection | Flat / fading | -0.137% / -0.143% / -0.072% | Position building in range | 49.1% | 0.0% | 50.9% | 9.04x | 0.382% / 0.227% |
| 2025-03-05 10:00 | 3.09x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.042% / 0.095% / 0.262% | False breakout | 39.5% | 53.5% | 7.0% | 0.65x | 0.553% / 0.357% |
| 2025-03-05 10:15 | 2.80x | Bullish pin-bar / lower rejection | Reversal | 0.053% / -0.071% / 0.463% | Liquidity sweep / reversal | 8.3% | 7.4% | 84.3% | 1.57x | 0.463% / 0.208% |
| 2025-03-05 12:00 | 3.51x | Bearish pin-bar / upper rejection | Reversal | -0.012% / -0.288% / -0.306% | Liquidity sweep / reversal | 37.2% | 49.6% | 13.1% | 2.25x | 0.165% / 0.505% |
| 2025-03-05 18:15 | 3.41x | Small-body bullish | Impulse / continuation | 0.082% / 0.082% / -0.304% | True breakout | 58.3% | 32.2% | 9.6% | 2.11x | 0.590% / 0.427% |
| 2025-03-05 19:00 | 3.98x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.356% / -0.514% / -0.526% | True breakout | 43.9% | 50.0% | 6.1% | 1.87x | 0.537% / 0.140% |
| 2025-03-05 22:30 | 2.40x | Bullish pin-bar / lower rejection | Flat / fading | -0.257% / -0.317% / -0.419% | Weak move without breakout | 44.0% | 0.0% | 56.0% | 1.32x | 0.628% / 0.150% |
| 2025-03-06 10:00 | 2.81x | Small-body bearish | Flat / fading | -0.178% / -0.137% / 0.006% | Weak move without breakout | 44.0% | 17.6% | 38.5% | 1.70x | 0.267% / 0.232% |
| 2025-03-07 08:30 | 2.65x | Full-bodied bullish | Impulse / continuation | -0.206% / -0.194% / 0.247% | True breakout | 88.7% | 5.7% | 5.7% | 2.87x | 0.276% / 0.206% |
| 2025-03-07 09:00 | 2.67x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.365% / 0.442% / 0.459% | True breakout | 2.6% | 94.7% | 2.6% | 0.98x | 0.683% / -0.012% |
| 2025-03-07 09:15 | 2.59x | Full-bodied bullish | Impulse / continuation | 0.076% / 0.070% / 0.857% | True breakout | 90.9% | 9.1% | 0.0% | 1.71x | 0.886% / 0.106% |
| 2025-03-07 10:00 | 6.29x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.762% / 1.401% / 1.319% | True breakout | 12.1% | 65.5% | 22.4% | 1.52x | 1.600% / 0.047% |
| 2025-03-07 10:15 | 6.73x | Full-bodied bullish | Impulse / continuation | 0.634% / 0.419% / 0.430% | True breakout | 90.9% | 3.5% | 5.6% | 3.52x | 0.832% / 0.087% |
| 2025-03-07 10:30 | 9.49x | Full-bodied bullish | Flat / fading | -0.214% / -0.081% / -0.162% | Weak move without breakout | 88.0% | 0.8% | 11.2% | 2.51x | 0.197% / 0.387% |
| 2025-03-07 10:45 | 3.63x | Bearish pin-bar / upper rejection | Flat / fading | 0.133% / 0.012% / 0.046% | Weak move without breakout | 39.8% | 45.8% | 14.5% | 1.50x | 0.174% / 0.307% |
| 2025-03-07 17:15 | 15.54x | Bullish pin-bar / lower rejection | Flat / fading | -0.859% / -0.518% / -1.488% | Position building in range | 48.6% | 0.3% | 51.1% | 15.28x | 1.547% / 0.100% |
| 2025-03-07 17:30 | 5.11x | Full-bodied bearish | Impulse / continuation | 0.344% / 0.089% / -0.457% | True breakout | 83.4% | 9.7% | 6.9% | 1.96x | 0.694% / 0.582% |
| 2025-03-07 17:45 | 3.17x | Bullish pin-bar / lower rejection | Reversal | -0.254% / -0.976% / -0.798% | Liquidity sweep / reversal | 34.5% | 23.4% | 42.1% | 1.72x | 0.237% / 1.035% |
| 2025-03-07 18:15 | 2.71x | Full-bodied bearish | Reversal | 0.179% / 0.179% / 0.836% | Liquidity sweep / reversal | 82.9% | 10.5% | 6.6% | 1.39x | 0.036% / 1.105% |
| 2025-03-07 20:15 | 2.56x | Full-bodied bullish | Flat / fading | -0.094% / 0.105% / -0.176% | Weak move without breakout | 73.2% | 21.1% | 5.7% | 1.77x | 0.392% / 0.258% |
| 2025-03-10 10:00 | 3.54x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.803% / -0.442% / -0.349% | True breakout | 37.9% | 40.9% | 21.2% | 1.69x | 0.989% / 0.145% |
| 2025-03-10 10:15 | 5.38x | Full-bodied bearish | Flat / fading | 0.364% / 0.399% / 0.293% | Position building in range | 70.3% | 13.3% | 16.4% | 4.62x | -0.006% / 0.551% |
| 2025-03-10 10:30 | 3.06x | Full-bodied bullish | Flat / fading | 0.035% / 0.093% / -0.129% | Weak move without breakout | 70.9% | 29.1% | 0.0% | 1.63x | 0.187% / 0.263% |
| 2025-03-10 14:00 | 3.68x | Full-bodied bullish | Flat / fading | 0.000% / -0.058% / -0.191% | Position building in range | 72.2% | 27.8% | 0.0% | 1.75x | 0.104% / 0.278% |
| 2025-03-10 20:30 | 2.94x | Full-bodied bearish | Flat / fading | 0.170% / 0.275% / 0.146% | Weak move without breakout | 71.2% | 0.0% | 28.8% | 2.42x | 0.006% / 0.591% |
| 2025-03-11 09:45 | 3.81x | Bullish pin-bar / lower rejection | Reversal | -0.088% / 0.117% / 0.609% | Liquidity sweep / reversal | 10.0% | 10.0% | 80.0% | 1.53x | 0.322% / 0.697% |
| 2025-03-11 10:00 | 6.51x | Bullish pin-bar / lower rejection | Reversal | 0.205% / 0.557% / 0.674% | Liquidity sweep / reversal | 19.7% | 23.9% | 56.3% | 2.09x | -0.012% / 0.920% |
| 2025-03-11 10:15 | 2.91x | Full-bodied bullish | Impulse / continuation | 0.351% / 0.491% / 0.433% | True breakout | 62.7% | 35.3% | 2.0% | 1.32x | 0.713% / 0.129% |
| 2025-03-11 10:30 | 3.23x | Full-bodied bullish | Impulse / continuation | 0.140% / 0.117% / -0.035% | True breakout | 74.4% | 0.0% | 25.6% | 2.04x | 0.361% / 0.204% |
| 2025-03-11 10:45 | 5.78x | Bullish pin-bar / lower rejection | Reversal | -0.023% / -0.058% / -0.291% | Liquidity sweep / reversal | 36.4% | 22.7% | 40.9% | 1.51x | 0.221% / 0.402% |
| 2025-03-11 11:00 | 4.01x | Doji / upper rejection | Impulse / continuation | -0.035% / -0.151% / -0.151% | True breakout | 0.0% | 76.4% | 23.6% | 1.28x | 0.384% / 0.384% |
| 2025-03-11 17:00 | 2.83x | Full-bodied bullish | Flat / fading | -0.017% / -0.203% / -0.209% | Position building in range | 61.1% | 36.7% | 2.2% | 2.14x | 0.041% / 0.296% |
| 2025-03-11 20:45 | 3.75x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.326% / -0.367% / -0.786% | True breakout | 37.5% | 62.5% | 0.0% | 2.52x | 1.426% / 0.466% |
| 2025-03-11 21:00 | 8.78x | Small-body bearish | Impulse / continuation | -0.041% / -0.397% / -0.432% | True breakout | 27.3% | 39.0% | 33.7% | 6.00x | 1.104% / 0.280% |
| 2025-03-11 21:45 | 4.23x | Bullish pin-bar / lower rejection | Reversal | 0.029% / -0.018% / 0.235% | Liquidity sweep / reversal | 7.9% | 13.6% | 78.6% | 2.73x | 0.411% / 0.335% |
| 2025-03-12 10:00 | 3.09x | Bullish pin-bar / lower rejection | Reversal | -0.123% / -0.298% / -0.620% | Liquidity sweep / reversal | 17.7% | 32.9% | 49.4% | 2.47x | 0.018% / 0.842% |
| 2025-03-12 10:30 | 2.76x | Full-bodied bearish | Impulse / continuation | -0.370% / -0.323% / -0.311% | True breakout | 76.9% | 2.6% | 20.5% | 1.03x | 0.546% / 0.070% |
| 2025-03-12 10:45 | 7.03x | Small-body bearish | Flat / fading | 0.047% / 0.118% / -0.106% | Position building in range | 60.0% | 11.4% | 28.6% | 3.01x | 0.135% / 0.247% |
| 2025-03-12 11:15 | 3.32x | Bullish pin-bar / lower rejection | Reversal | -0.059% / -0.224% / -0.006% | Liquidity sweep / reversal | 27.9% | 0.0% | 72.1% | 1.04x | 0.218% / 0.235% |
| 2025-03-13 07:45 | 3.74x | Full-bodied bearish | Flat / fading | 0.141% / 0.135% / 0.118% | Position building in range | 84.4% | 7.8% | 7.8% | 3.14x | 0.029% / 0.335% |
| 2025-03-13 09:00 | 4.94x | Full-bodied bearish | Impulse / continuation | 0.018% / -0.024% / 0.018% | True breakout | 96.1% | 3.9% | 0.0% | 1.91x | 0.177% / 0.194% |
| 2025-03-13 10:00 | 4.12x | Bearish pin-bar / upper rejection | Reversal | -0.035% / -0.377% / -0.843% | Liquidity sweep / reversal | 10.4% | 62.5% | 27.1% | 1.41x | 0.112% / 0.878% |
| 2025-03-13 10:15 | 2.85x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.342% / -0.454% / -0.967% | True breakout | 12.2% | 38.8% | 49.0% | 1.32x | 1.020% / 0.000% |
| 2025-03-13 10:30 | 5.89x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.112% / -0.467% / -0.432% | True breakout | 53.2% | 0.0% | 46.8% | 2.82x | 0.680% / 0.030% |
| 2025-03-13 11:00 | 5.49x | Full-bodied bearish | Impulse / continuation | -0.160% / 0.036% / -0.053% | True breakout | 89.2% | 1.5% | 9.2% | 1.50x | 0.576% / 0.137% |
| 2025-03-13 12:00 | 2.92x | Small-body bullish | Impulse / continuation | 0.137% / 0.054% / 0.505% | True breakout | 46.1% | 23.5% | 30.4% | 2.34x | 0.618% / 0.071% |
| 2025-03-13 15:45 | 2.18x | Bearish pin-bar / upper rejection | Flat / fading | -0.042% / 0.396% / 0.312% | Weak move without breakout | 50.6% | 43.7% | 5.7% | 1.18x | 0.510% / 0.396% |
| 2025-03-13 19:00 | 9.12x | Bearish pin-bar / upper rejection | Flat / fading | 0.488% / 0.735% / 0.447% | Weak move without breakout | 14.7% | 63.9% | 21.5% | 2.81x | 0.976% / 0.018% |
| 2025-03-13 19:15 | 3.07x | Full-bodied bullish | Flat / fading | 0.246% / -0.053% / -0.170% | Weak move without breakout | 70.4% | 25.2% | 4.3% | 1.34x | 0.486% / 0.574% |
| 2025-03-14 10:00 | 2.99x | Small-body bullish | Flat / fading | 0.183% / 0.018% / -0.030% | Weak move without breakout | 57.1% | 16.1% | 26.8% | 1.26x | 0.224% / 0.142% |
| 2025-03-14 11:30 | 2.75x | Full-bodied bearish | Flat / fading | -0.142% / 0.101% / 0.196% | Weak move without breakout | 74.7% | 2.1% | 23.2% | 2.84x | 0.172% / 0.291% |
| 2025-03-14 16:00 | 2.89x | Full-bodied bullish | Impulse / continuation | 0.070% / 0.631% / 0.310% | True breakout | 75.0% | 0.0% | 25.0% | 2.29x | 0.766% / 0.169% |
| 2025-03-14 16:15 | 4.20x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.561% / 0.543% / -0.023% | True breakout | 23.6% | 56.4% | 20.0% | 1.20x | 0.695% / 0.239% |
| 2025-03-14 16:30 | 4.98x | Small-body bullish | Reversal | -0.017% / -0.319% / -0.627% | Liquidity sweep / reversal | 59.4% | 14.4% | 26.3% | 3.55x | 0.110% / 0.668% |
| 2025-03-15 16:15 | 2.78x | Bullish pin-bar / lower rejection | Reversal | -0.041% / -0.006% / 0.029% | Liquidity sweep / reversal | 56.3% | 0.0% | 43.7% | 2.29x | 0.058% / 0.064% |
| 2025-03-16 16:00 | 24.87x | Full-bodied bullish | Impulse / continuation | 0.202% / 0.723% / 0.919% | True breakout | 75.9% | 24.1% | 0.0% | 36.31x | 1.040% / 0.052% |
| 2025-03-16 16:15 | 12.82x | Full-bodied bullish | Impulse / continuation | 0.519% / 0.525% / 0.663% | True breakout | 71.4% | 10.2% | 18.4% | 6.12x | 0.836% / 0.046% |
| 2025-03-16 16:30 | 17.87x | Full-bodied bullish | Impulse / continuation | 0.006% / 0.195% / 0.115% | True breakout | 73.2% | 20.3% | 6.5% | 10.83x | 0.316% / 0.258% |
| 2025-03-16 16:45 | 5.99x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.189% / 0.138% / 0.184% | True breakout | 1.8% | 16.4% | 81.8% | 2.75x | 0.310% / 0.069% |
| 2025-03-16 17:00 | 6.58x | Small-body bullish | Flat / fading | -0.052% / -0.080% / -0.109% | Weak move without breakout | 59.3% | 38.9% | 1.9% | 2.27x | 0.120% / 0.258% |
| 2025-03-16 17:15 | 2.76x | Bearish pin-bar / upper rejection | Reversal | -0.029% / 0.046% / 0.086% | Liquidity sweep / reversal | 21.7% | 43.5% | 34.8% | 1.67x | 0.206% / 0.115% |
| 2025-03-17 07:00 | 6.84x | Full-bodied bullish | Impulse / continuation | -0.046% / 0.239% / 0.684% | True breakout | 60.8% | 10.8% | 28.3% | 2.77x | 0.866% / 0.142% |
| 2025-03-17 07:45 | 2.56x | Full-bodied bullish | Flat / fading | -0.011% / -0.209% / -0.164% | Position building in range | 73.5% | 26.5% | 0.0% | 2.30x | 0.028% / 0.413% |
| 2025-03-17 10:00 | 2.72x | Full-bodied bearish | Flat / fading | 0.074% / 0.210% / 0.273% | Position building in range | 65.8% | 19.7% | 14.5% | 1.59x | 0.040% / 0.330% |
| 2025-03-17 14:45 | 9.65x | Bullish pin-bar / lower rejection | Flat / fading | 0.199% / 0.170% / 0.204% | Position building in range | 28.6% | 1.6% | 69.8% | 10.03x | 0.023% / 0.312% |
| 2025-03-18 07:00 | 12.72x | Full-bodied bullish | Impulse / continuation | 0.293% / 0.383% / 0.344% | True breakout | 62.5% | 26.9% | 10.6% | 8.13x | 0.439% / 0.006% |
| 2025-03-18 07:15 | 3.17x | Full-bodied bullish | Flat / fading | 0.090% / -0.095% / 0.101% | Weak move without breakout | 75.4% | 23.2% | 1.4% | 3.65x | 0.146% / 0.101% |
| 2025-03-18 08:45 | 3.29x | Bearish pin-bar / upper rejection | Flat / fading | -0.022% / 0.000% / 0.112% | Weak move without breakout | 39.6% | 58.3% | 2.1% | 1.70x | 0.163% / 0.084% |
| 2025-03-18 10:00 | 4.81x | Full-bodied bearish | Flat / fading | -0.028% / -0.034% / -0.112% | Weak move without breakout | 69.1% | 2.9% | 27.9% | 2.03x | 0.224% / 0.163% |
| 2025-03-18 10:30 | 2.67x | Bullish pin-bar / lower rejection | Flat / fading | 0.022% / -0.079% / -0.067% | Weak move without breakout | 14.0% | 7.0% | 79.1% | 1.11x | 0.135% / 0.107% |
| 2025-03-18 16:00 | 9.13x | Small-body bullish | Impulse / continuation | 0.341% / 0.854% / 0.715% | True breakout | 51.4% | 35.8% | 12.7% | 10.09x | 1.016% / 0.045% |
| 2025-03-18 16:15 | 4.97x | Full-bodied bullish | Impulse / continuation | 0.512% / 0.206% / 0.312% | True breakout | 82.7% | 8.0% | 9.3% | 2.68x | 0.673% / 0.022% |
| 2025-03-18 16:30 | 4.77x | Full-bodied bullish | Flat / fading | -0.305% / -0.138% / -0.066% | Weak move without breakout | 86.0% | 10.3% | 3.7% | 3.26x | 0.161% / 0.338% |
| 2025-03-18 16:45 | 2.71x | Full-bodied bearish | Reversal | 0.167% / 0.106% / 0.861% | Liquidity sweep / reversal | 61.1% | 32.2% | 6.7% | 2.29x | 0.006% / 0.939% |
| 2025-03-18 18:00 | 3.62x | Bearish pin-bar / upper rejection | Reversal | -0.324% / -0.731% / -0.495% | Liquidity sweep / reversal | 37.5% | 59.1% | 3.4% | 1.49x | 0.044% / 1.583% |
| 2025-03-18 18:15 | 6.64x | Bullish pin-bar / lower rejection | Reversal | -0.408% / -0.331% / 0.441% | Liquidity sweep / reversal | 21.3% | 1.4% | 77.4% | 4.58x | 0.585% / 0.524% |
| 2025-03-18 19:45 | 2.91x | Bullish pin-bar / lower rejection | Flat / fading | -0.050% / -0.750% / -1.279% | Weak move without breakout | 16.1% | 2.1% | 81.8% | 2.87x | 1.412% / 0.072% |
| 2025-03-18 20:15 | 3.71x | Bullish pin-bar / lower rejection | Flat / fading | -0.211% / -0.533% / -0.111% | Weak move without breakout | 50.0% | 9.3% | 40.7% | 2.23x | 0.667% / 0.811% |
| 2025-03-19 10:00 | 3.72x | Full-bodied bearish | Flat / fading | 0.045% / 0.281% / 0.236% | Position building in range | 68.5% | 6.3% | 25.2% | 2.66x | 0.157% / 0.461% |
| 2025-03-19 18:15 | 2.80x | Bearish pin-bar / upper rejection | Flat / fading | 0.077% / 0.138% / 0.249% | Weak move without breakout | 50.7% | 49.3% | 0.0% | 1.83x | 0.331% / 0.110% |
| 2025-03-20 07:00 | 6.59x | Full-bodied bullish | Impulse / continuation | 0.502% / 0.382% / 0.147% | True breakout | 81.5% | 18.5% | 0.0% | 6.31x | 0.557% / 0.240% |
| 2025-03-20 07:15 | 3.74x | Full-bodied bullish | Flat / fading | -0.119% / 0.011% / -0.353% | Weak move without breakout | 92.9% | 0.0% | 7.1% | 3.78x | 0.054% / 0.739% |
| 2025-03-20 07:30 | 2.50x | Small-body bearish | Reversal | 0.130% / -0.234% / -0.223% | Liquidity sweep / reversal | 47.8% | 21.7% | 30.4% | 1.43x | 0.620% / 0.174% |
| 2025-03-20 10:00 | 12.24x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.115% / -0.399% / -0.689% | True breakout | 48.6% | 7.3% | 44.1% | 2.85x | 0.919% / 0.148% |
| 2025-03-20 10:30 | 2.80x | Small-body bearish | Flat / fading | -0.236% / -0.291% / -0.154% | Weak move without breakout | 47.2% | 13.0% | 39.8% | 1.43x | 0.522% / 0.192% |
| 2025-03-20 10:45 | 2.87x | Bullish pin-bar / lower rejection | Reversal | -0.055% / 0.292% / -0.072% | Liquidity sweep / reversal | 44.8% | 1.0% | 54.2% | 1.29x | 0.226% / 0.429% |
| 2025-03-20 15:15 | 3.64x | Full-bodied bearish | Reversal | 0.000% / 0.339% / 1.028% | Liquidity sweep / reversal | 82.7% | 1.6% | 15.7% | 3.40x | 0.072% / 1.033% |
| 2025-03-21 07:00 | 10.37x | Bearish pin-bar / upper rejection | Reversal | -0.208% / -0.318% / -0.329% | Liquidity sweep / reversal | 37.0% | 41.7% | 21.3% | 5.62x | 0.027% / 0.428% |
| 2025-03-21 07:15 | 2.84x | Bullish pin-bar / lower rejection | Flat / fading | -0.110% / 0.000% / -0.066% | Weak move without breakout | 51.9% | 2.5% | 45.6% | 3.06x | 0.220% / 0.170% |
| 2025-03-21 10:00 | 5.20x | Bullish pin-bar / lower rejection | Reversal | -0.033% / -0.115% / 0.104% | Liquidity sweep / reversal | 14.0% | 22.0% | 64.0% | 1.25x | 0.104% / 0.159% |
| 2025-03-21 13:30 | 9.25x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.170% / -0.275% / -0.654% | True breakout | 41.4% | 0.0% | 58.6% | 5.89x | 0.857% / 0.033% |
| 2025-03-21 14:15 | 3.18x | Full-bodied bearish | Impulse / continuation | -0.055% / -0.094% / -0.166% | True breakout | 65.6% | 6.7% | 27.8% | 2.64x | 0.332% / 0.249% |
| 2025-03-24 07:00 | 3.72x | Full-bodied bearish | Impulse / continuation | -0.055% / -0.078% / -0.017% | True breakout | 71.4% | 28.6% | 0.0% | 2.93x | 0.222% / 0.139% |
| 2025-03-24 07:15 | 2.76x | Bullish pin-bar / lower rejection | Flat / fading | -0.022% / 0.089% / -0.011% | Weak move without breakout | 34.8% | 0.0% | 65.2% | 1.65x | 0.050% / 0.194% |
| 2025-03-24 10:00 | 6.69x | Small-body bearish | Impulse / continuation | 0.006% / -0.161% / -0.022% | True breakout | 34.7% | 32.0% | 33.3% | 2.32x | 0.411% / 0.161% |
| 2025-03-24 10:45 | 4.53x | Bullish pin-bar / lower rejection | Reversal | 0.184% / 0.083% / 0.217% | Liquidity sweep / reversal | 10.0% | 37.1% | 52.9% | 2.07x | 0.078% / 0.312% |
| 2025-03-24 11:00 | 3.41x | Small-body bullish | Impulse / continuation | -0.100% / -0.039% / 0.317% | True breakout | 52.9% | 32.9% | 14.3% | 1.97x | 0.394% / 0.194% |
| 2025-03-24 21:00 | 6.62x | Full-bodied bearish | Impulse / continuation | -0.156% / 0.139% / -0.033% | True breakout | 70.4% | 0.6% | 29.0% | 6.59x | 0.485% / 0.184% |
| 2025-03-24 21:15 | 5.02x | Bullish pin-bar / lower rejection | Reversal | 0.296% / 0.151% / 0.140% | Liquidity sweep / reversal | 24.3% | 24.3% | 51.3% | 3.38x | 0.128% / 0.340% |
| 2025-03-25 10:00 | 3.80x | Full-bodied bearish | Impulse / continuation | 0.072% / -0.055% / 0.017% | True breakout | 75.9% | 24.1% | 0.0% | 1.56x | 0.105% / 0.354% |
| 2025-03-25 11:00 | 7.83x | Bearish pin-bar / upper rejection | Reversal | -0.072% / -0.061% / -0.050% | Liquidity sweep / reversal | 11.4% | 87.1% | 1.4% | 3.62x | 0.116% / 0.149% |
| 2025-03-25 12:15 | 4.32x | Full-bodied bearish | Impulse / continuation | -0.011% / -0.256% / -0.401% | True breakout | 79.0% | 1.0% | 20.0% | 3.78x | 0.545% / 0.111% |
| 2025-03-25 12:30 | 3.68x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.245% / -0.228% / -0.395% | True breakout | 3.0% | 29.9% | 67.2% | 2.03x | 0.534% / 0.022% |
| 2025-03-25 12:45 | 3.79x | Full-bodied bearish | Flat / fading | 0.017% / -0.145% / -0.022% | Weak move without breakout | 62.9% | 5.7% | 31.4% | 1.94x | 0.290% / 0.145% |
| 2025-03-25 17:00 | 3.20x | Full-bodied bearish | Impulse -> reversal | -0.062% / -0.315% / 0.870% | False breakout | 80.2% | 10.8% | 9.0% | 3.64x | 0.382% / 0.882% |
| 2025-03-25 17:45 | 4.61x | Full-bodied bullish | Impulse / continuation | 0.240% / 0.262% / 0.279% | True breakout | 92.8% | 0.0% | 7.2% | 4.64x | 0.374% / 0.251% |
| 2025-03-26 07:00 | 2.74x | Bearish pin-bar / upper rejection | Reversal | 0.044% / 0.033% / 0.044% | Liquidity sweep / reversal | 2.1% | 87.2% | 10.6% | 2.28x | 0.011% / 0.121% |
| 2025-03-26 10:00 | 4.55x | Full-bodied bearish | Impulse / continuation | -0.078% / -0.028% / 0.066% | True breakout | 70.2% | 17.5% | 12.3% | 2.81x | 0.199% / 0.066% |
| 2025-03-26 10:15 | 3.16x | Small-body bearish | Reversal | 0.050% / -0.022% / 0.139% | Liquidity sweep / reversal | 50.0% | 16.7% | 33.3% | 1.27x | 0.122% / 0.205% |
| 2025-03-26 14:30 | 2.92x | Bullish pin-bar / lower rejection | Flat / fading | -0.172% / 0.006% / -0.200% | Weak move without breakout | 20.0% | 10.0% | 70.0% | 1.70x | 0.316% / 0.067% |
| 2025-03-26 15:45 | 2.89x | Full-bodied bearish | Impulse / continuation | -0.011% / 0.179% / -0.017% | True breakout | 67.9% | 0.0% | 32.1% | 2.32x | 0.346% / 0.268% |
| 2025-03-26 16:30 | 2.58x | Small-body bearish | Flat / fading | -0.039% / 0.000% / -0.167% | Weak move without breakout | 43.1% | 24.6% | 32.3% | 1.56x | 0.251% / 0.100% |
| 2025-03-27 10:00 | 8.40x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.216% / -0.278% / -0.312% | True breakout | 44.4% | 11.1% | 44.4% | 2.83x | 0.624% / 0.011% |
| 2025-03-27 10:15 | 5.47x | Bullish pin-bar / lower rejection | Flat / fading | -0.063% / 0.028% / -0.290% | Position building in range | 35.7% | 0.0% | 64.3% | 2.02x | 0.347% / 0.199% |
| 2025-03-27 10:30 | 3.04x | Bullish pin-bar / lower rejection | Reversal | 0.091% / -0.034% / -0.188% | Liquidity sweep / reversal | 14.6% | 33.3% | 52.1% | 1.54x | 0.501% / 0.262% |
| 2025-03-27 14:15 | 2.16x | Bearish pin-bar / upper rejection | Reversal | -0.347% / -0.602% / -1.222% | Liquidity sweep / reversal | 44.4% | 53.7% | 1.9% | 1.07x | 0.057% / 1.449% |
| 2025-03-27 15:00 | 2.14x | Small-body bearish | Impulse / continuation | -0.189% / -0.459% / -1.286% | True breakout | 57.0% | 19.0% | 23.9% | 2.62x | 1.498% / 0.121% |
| 2025-03-27 15:45 | 3.68x | Full-bodied bearish | Flat / fading | 0.134% / 0.175% / 0.466% | Weak move without breakout | 94.9% | 2.3% | 2.8% | 2.74x | 0.239% / 0.833% |
| 2025-03-27 16:00 | 2.40x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.041% / 0.390% / 0.471% | True breakout | 30.3% | 51.3% | 18.4% | 1.04x | 0.744% / 0.372% |
| 2025-03-28 07:00 | 3.49x | Bullish pin-bar / lower rejection | Reversal | 0.284% / 0.390% / 0.597% | Liquidity sweep / reversal | 50.7% | 0.7% | 48.6% | 2.72x | 0.307% / 0.863% |
| 2025-03-28 10:00 | 4.82x | Full-bodied bullish | Impulse / continuation | 0.434% / 0.685% / 0.984% | True breakout | 84.2% | 5.8% | 10.0% | 2.38x | 1.353% / 0.275% |
| 2025-03-28 10:15 | 3.44x | Small-body bullish | Impulse / continuation | 0.251% / 0.671% / 0.507% | True breakout | 51.4% | 18.2% | 30.4% | 1.65x | 0.916% / 0.134% |
| 2025-03-28 10:30 | 3.09x | Small-body bullish | Flat / fading | 0.419% / 0.297% / 0.041% | Weak move without breakout | 39.0% | 34.0% | 27.0% | 1.00x | 0.663% / 0.087% |
| 2025-03-28 10:45 | 3.44x | Full-bodied bullish | Reversal | -0.122% / -0.162% / -0.649% | Liquidity sweep / reversal | 75.5% | 14.7% | 9.8% | 1.05x | 0.243% / 0.776% |
| 2025-03-28 12:45 | 2.12x | Bullish pin-bar / lower rejection | Reversal | 0.065% / 0.141% / 0.123% | Liquidity sweep / reversal | 1.0% | 26.5% | 72.5% | 1.06x | 0.346% / 0.505% |
| 2025-03-28 14:45 | 3.78x | Full-bodied bearish | Impulse / continuation | -0.577% / -0.342% / -0.174% | True breakout | 93.8% | 1.2% | 5.0% | 2.93x | 1.310% / 0.451% |
| 2025-03-28 15:00 | 3.23x | Bullish pin-bar / lower rejection | Flat / fading | 0.236% / 0.568% / 0.224% | Position building in range | 32.1% | 26.3% | 41.6% | 2.89x | 0.278% / 0.840% |
| 2025-03-30 13:00 | 3.13x | Doji | Flat / fading | 0.000% / 0.000% / 0.000% | Position building in range | 0.0% | 0.0% | 0.0% | n/a | 0.000% / 0.000% |
| 2025-03-30 17:00 | 2.93x | Doji | Flat / fading | 0.000% / 0.000% / 0.000% | Position building in range | 0.0% | 0.0% | 0.0% | n/a | 0.000% / 0.000% |
| 2025-03-30 18:45 | 5.20x | Doji | Impulse / continuation | -1.333% / 0.295% / 0.037% | True breakout | 0.0% | 0.0% | 0.0% | n/a | 1.702% / 1.702% |
| 2025-03-31 06:45 | 39.23x | Doji | Impulse / continuation | 1.650% / 1.538% / 2.260% | True breakout | 0.0% | 0.0% | 0.0% | n/a | 2.491% / 2.491% |
| 2025-03-31 07:00 | 297.89x | Small-body bullish | Flat / fading | -0.110% / -0.257% / 0.490% | Position building in range | 57.6% | 29.3% | 13.0% | 29.68x | 0.766% / 0.821% |
| 2025-03-31 07:15 | 6.35x | Bullish pin-bar / lower rejection | Reversal | -0.147% / 0.711% / 0.932% | Liquidity sweep / reversal | 10.8% | 15.8% | 73.4% | 3.27x | 0.656% / 1.012% |
| 2025-03-31 07:30 | 3.00x | Bullish pin-bar / lower rejection | Reversal | 0.860% / 0.749% / 2.223% | Liquidity sweep / reversal | 17.9% | 24.8% | 57.2% | 2.43x | 0.264% / 2.469% |
| 2025-03-31 07:45 | 3.31x | Full-bodied bullish | Impulse / continuation | -0.110% / 0.219% / 1.230% | True breakout | 78.3% | 0.5% | 21.2% | 2.63x | 1.595% / 0.444% |
| 2025-03-31 08:00 | 2.58x | Bullish pin-bar / lower rejection | Reversal | 0.329% / 1.463% / 1.920% | Liquidity sweep / reversal | 16.0% | 29.0% | 55.0% | 1.20x | 0.183% / 2.042% |
| 2025-03-31 08:30 | 4.44x | Full-bodied bullish | Flat / fading | -0.120% / 0.451% / 0.138% | Weak move without breakout | 81.8% | 18.2% | 0.0% | 2.26x | 0.571% / 0.523% |
| 2025-03-31 09:00 | 3.56x | Full-bodied bullish | Flat / fading | -0.323% / -0.311% / 0.012% | Weak move without breakout | 82.1% | 17.9% | 0.0% | 0.93x | 0.431% / 0.867% |
| 2025-03-31 10:00 | 3.05x | Bearish pin-bar / upper rejection | Reversal | -0.299% / -0.981% / -0.789% | Liquidity sweep / reversal | 51.9% | 44.3% | 3.8% | 1.03x | 0.305% / 1.842% |
| 2025-03-31 10:45 | 2.69x | Full-bodied bearish | Reversal | 1.060% / 0.457% / 0.189% | Liquidity sweep / reversal | 99.3% | 0.0% | 0.7% | 1.05x | 0.012% / 1.365% |
| 2025-04-01 07:00 | 10.20x | Full-bodied bullish | Impulse / continuation | 0.289% / 0.265% / 0.260% | True breakout | 77.0% | 23.0% | 0.0% | 7.48x | 0.425% / 0.059% |
| 2025-04-01 07:15 | 3.86x | Full-bodied bullish | Flat / fading | -0.024% / 0.065% / -0.288% | Weak move without breakout | 83.3% | 1.7% | 15.0% | 2.14x | 0.135% / 0.306% |
| 2025-04-01 07:30 | 3.03x | Doji / upper rejection | Impulse / continuation | 0.088% / -0.006% / -0.100% | True breakout | 0.0% | 73.0% | 27.0% | 1.21x | 0.282% / 0.282% |
| 2025-04-01 10:00 | 4.77x | Small-body bullish | Flat / fading | -0.212% / -0.200% / -0.012% | Position building in range | 38.4% | 32.3% | 29.3% | 2.28x | 0.071% / 0.311% |
| 2025-04-01 13:45 | 3.16x | Full-bodied bearish | Impulse / continuation | -0.372% / -0.389% / -1.133% | True breakout | 68.3% | 1.6% | 30.1% | 2.84x | 1.281% / 0.089% |
| 2025-04-01 14:30 | 3.68x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.422% / -0.226% / -0.701% | True breakout | 45.8% | 0.8% | 53.3% | 2.23x | 0.898% / 0.279% |
| 2025-04-01 14:45 | 3.13x | Small-body bearish | Flat / fading | 0.197% / -0.304% / 0.048% | Weak move without breakout | 49.7% | 32.9% | 17.5% | 2.41x | 0.478% / 0.489% |
| 2025-04-01 17:30 | 2.84x | Bearish pin-bar / upper rejection | Reversal | 0.368% / 0.143% / -0.695% | Liquidity sweep / reversal | 50.9% | 44.7% | 4.4% | 2.36x | 0.784% / 0.974% |
| 2025-04-02 07:00 | 3.51x | Full-bodied bullish | Flat / fading | -0.346% / -0.419% / -0.097% | Weak move without breakout | 85.9% | 7.3% | 6.8% | 2.16x | 0.170% / 0.905% |
| 2025-04-02 10:00 | 3.98x | Bullish pin-bar / lower rejection | Reversal | 0.006% / 0.049% / -0.322% | Liquidity sweep / reversal | 35.2% | 23.2% | 41.5% | 1.48x | 0.273% / 0.431% |
| 2025-04-02 16:45 | 2.75x | Full-bodied bearish | Flat / fading | 0.624% / 0.501% / 0.300% | Position building in range | 81.9% | 2.7% | 15.4% | 3.23x | 0.049% / 0.813% |
| 2025-04-02 19:00 | 5.26x | Bullish pin-bar / lower rejection | Reversal | -0.315% / 0.241% / 0.432% | Liquidity sweep / reversal | 39.7% | 16.1% | 44.3% | 2.61x | 0.475% / 0.432% |
| 2025-04-03 07:00 | 4.10x | Full-bodied bullish | Flat / fading | 0.198% / 0.168% / -0.102% | Weak move without breakout | 71.9% | 10.4% | 17.8% | 2.06x | 0.282% / 0.186% |
| 2025-04-03 14:15 | 2.80x | Bullish pin-bar / lower rejection | Flat / fading | -0.519% / -0.244% / -0.342% | Weak move without breakout | 56.6% | 0.0% | 43.4% | 2.65x | 0.861% / 0.055% |
| 2025-04-03 17:00 | 2.54x | Bullish pin-bar / lower rejection | Flat / fading | -0.111% / 0.105% / -0.285% | Weak move without breakout | 31.3% | 14.8% | 53.9% | 1.35x | 0.458% / 0.353% |
| 2025-04-03 19:15 | 2.47x | Bullish pin-bar / lower rejection | Reversal | 0.168% / 0.505% / 0.274% | Liquidity sweep / reversal | 28.5% | 5.3% | 66.2% | 2.07x | 0.037% / 0.829% |
| 2025-04-04 07:00 | 6.13x | Small-body bearish | Impulse / continuation | -0.560% / -0.432% / -0.651% | True breakout | 54.3% | 18.6% | 27.1% | 3.00x | 0.870% / 0.000% |
| 2025-04-04 13:15 | 4.39x | Full-bodied bearish | Impulse / continuation | 0.088% / -0.950% / -0.699% | True breakout | 65.3% | 10.6% | 24.1% | 1.97x | 1.202% / 0.535% |
| 2025-04-04 13:45 | 3.53x | Full-bodied bearish | Flat / fading | 0.311% / 0.254% / -0.241% | Weak move without breakout | 70.8% | 16.3% | 12.9% | 2.56x | 0.686% / 0.845% |
| 2025-04-04 14:00 | 2.48x | Small-body bullish | Reversal | -0.057% / -0.519% / -1.153% | Liquidity sweep / reversal | 38.3% | 33.1% | 28.6% | 1.31x | 0.532% / 1.609% |
| 2025-04-04 15:00 | 2.25x | Small-body bearish | Reversal | 0.135% / 0.679% / 0.211% | Liquidity sweep / reversal | 51.4% | 9.3% | 39.3% | 1.55x | 0.256% / 0.730% |
| 2025-04-05 15:30 | 2.87x | Full-bodied bearish | Flat / fading | -0.264% / -0.139% / 0.369% | Weak move without breakout | 69.7% | 7.7% | 22.6% | 2.55x | 0.297% / 0.369% |
| 2025-04-06 11:30 | 2.94x | Bearish pin-bar / upper rejection | Flat / fading | -0.033% / 0.007% / 0.208% | Weak move without breakout | 36.6% | 52.1% | 11.3% | 1.71x | 0.286% / 0.156% |
| 2025-04-06 16:30 | 2.67x | Small-body bullish | Reversal | 0.000% / -0.277% / 0.090% | Liquidity sweep / reversal | 58.0% | 27.5% | 14.5% | 1.72x | 0.116% / 0.412% |
| 2025-04-07 07:00 | 13.31x | Full-bodied bearish | Impulse / continuation | 0.315% / -0.944% / -0.603% | True breakout | 73.5% | 23.2% | 3.3% | 3.88x | 2.263% / 0.944% |
| 2025-04-07 07:15 | 5.35x | Bearish pin-bar / upper rejection | Reversal | -1.255% / -0.701% / -1.141% | Liquidity sweep / reversal | 22.8% | 45.6% | 31.6% | 2.37x | 0.154% / 2.570% |
| 2025-04-07 07:30 | 6.32x | Bullish pin-bar / lower rejection | Flat / fading | 0.561% / 0.345% / -0.243% | Weak move without breakout | 49.1% | 0.8% | 50.1% | 3.95x | 0.967% / 1.426% |
| 2025-04-07 09:30 | 3.17x | Bullish pin-bar / lower rejection | Reversal | 1.279% / 1.908% / 3.014% | Liquidity sweep / reversal | 54.9% | 2.7% | 42.3% | 1.68x | 0.221% / 3.249% |
| 2025-04-07 10:00 | 2.33x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.068% / 1.085% / 1.621% | True breakout | 36.3% | 6.0% | 57.8% | 1.22x | 2.436% / 0.746% |
| 2025-04-07 16:45 | 2.54x | Full-bodied bullish | Impulse / continuation | 1.972% / 0.105% / 1.183% | True breakout | 84.5% | 9.4% | 6.0% | 2.75x | 5.133% / 0.749% |
| 2025-04-07 17:00 | 3.28x | Full-bodied bullish | Impulse / continuation | -1.831% / -0.773% / -1.773% | True breakout | 79.2% | 9.2% | 11.6% | 2.49x | 3.100% / 2.669% |
| 2025-04-07 17:15 | 11.88x | Bearish pin-bar / upper rejection | Flat / fading | 1.077% / 1.077% / 0.112% | Position building in range | 31.7% | 53.7% | 14.5% | 5.48x | 0.630% / 1.714% |
| 2025-04-07 17:30 | 3.13x | Small-body bullish | Flat / fading | 0.000% / -1.007% / -0.643% | Weak move without breakout | 55.4% | 12.8% | 31.9% | 1.35x | 0.630% / 1.416% |
| 2025-04-08 07:00 | 5.33x | Bearish pin-bar / upper rejection | Flat / fading | -0.160% / 0.230% / 0.403% | Weak move without breakout | 28.0% | 60.3% | 11.6% | 2.00x | 0.915% / 0.198% |
| 2025-04-08 10:00 | 2.75x | Full-bodied bearish | Impulse / continuation | -0.135% / -0.699% / -0.737% | True breakout | 68.8% | 7.2% | 24.0% | 1.32x | 0.949% / 0.026% |
| 2025-04-08 19:30 | 2.77x | Full-bodied bearish | Impulse / continuation | -0.904% / -0.878% / 0.039% | True breakout | 77.4% | 0.4% | 22.2% | 3.29x | 1.376% / 0.413% |
| 2025-04-08 19:45 | 3.14x | Full-bodied bearish | Reversal | 0.026% / 0.185% / 0.893% | Liquidity sweep / reversal | 71.9% | 18.4% | 9.7% | 2.12x | 0.476% / 1.329% |
| 2025-04-08 20:30 | 2.10x | Small-body bullish | Reversal | -0.059% / -0.485% / -0.911% | Liquidity sweep / reversal | 44.1% | 22.3% | 33.6% | 2.44x | 0.138% / 0.970% |
| 2025-04-09 07:00 | 2.22x | Bullish pin-bar / lower rejection | Flat / fading | 0.188% / 0.342% / 0.638% | Weak move without breakout | 7.6% | 24.4% | 68.0% | 1.96x | 0.987% / 0.221% |
| 2025-04-09 10:00 | 4.85x | Bearish pin-bar / upper rejection | Reversal | 0.219% / 0.729% / 0.935% | Liquidity sweep / reversal | 49.6% | 47.5% | 2.9% | 2.28x | 0.239% / 1.034% |
| 2025-04-09 14:00 | 5.40x | Full-bodied bearish | Flat / fading | 0.956% / 0.021% / 1.205% | Weak move without breakout | 81.7% | 3.3% | 15.0% | 3.38x | 0.429% / 1.434% |
| 2025-04-09 20:15 | 6.48x | Small-body bullish | Impulse / continuation | 0.921% / 3.257% / 2.204% | True breakout | 48.8% | 25.0% | 26.2% | 4.63x | 3.322% / 0.039% |
| 2025-04-09 20:30 | 3.91x | Bearish pin-bar / upper rejection | Impulse / continuation | 2.314% / 1.395% / 0.958% | True breakout | 42.9% | 56.2% | 0.9% | 2.34x | 2.379% / 0.104% |
| 2025-04-09 20:45 | 2.75x | Full-bodied bullish | Flat / fading | -0.898% / -1.019% / -2.083% | Weak move without breakout | 95.4% | 0.3% | 4.3% | 2.37x | 0.064% / 2.096% |
| 2025-04-11 09:00 | 8.52x | Full-bodied bullish | Impulse / continuation | 0.070% / 0.311% / 0.140% | True breakout | 96.6% | 2.8% | 0.6% | 5.47x | 0.521% / 0.641% |
| 2025-04-11 09:15 | 6.62x | Bullish pin-bar / lower rejection | Flat / fading | 0.241% / 0.133% / 0.082% | Weak move without breakout | 4.5% | 28.2% | 67.3% | 3.73x | 0.450% / 0.628% |
| 2025-04-11 09:30 | 4.36x | Small-body bullish | Flat / fading | -0.108% / -0.171% / -0.133% | Weak move without breakout | 53.0% | 39.8% | 7.2% | 1.62x | 0.127% / 0.867% |
| 2025-04-11 10:00 | 3.87x | Bullish pin-bar / lower rejection | Reversal | 0.013% / 0.038% / 0.127% | Liquidity sweep / reversal | 4.4% | 14.7% | 80.9% | 2.46x | 0.418% / 0.298% |
| 2025-04-11 11:00 | 2.86x | Bullish pin-bar / lower rejection | Flat / fading | -0.228% / -0.519% / -0.576% | Weak move without breakout | 10.8% | 4.9% | 84.3% | 1.57x | 0.741% / 0.139% |
| 2025-04-12 17:45 | 3.42x | Small-body bullish | Flat / fading | -0.050% / 0.013% / 0.000% | Weak move without breakout | 40.0% | 36.0% | 24.0% | 2.73x | 0.063% / 0.075% |
| 2025-04-12 18:45 | 4.15x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.006% / 0.031% / -0.075% | True breakout | 50.0% | 50.0% | 0.0% | 0.89x | 0.843% / 0.063% |
| 2025-04-13 10:00 | 12.34x | Bullish pin-bar / lower rejection | Reversal | -0.094% / -0.107% / -0.132% | Liquidity sweep / reversal | 4.9% | 3.5% | 91.7% | 13.18x | 0.025% / 0.151% |
| 2025-04-13 11:30 | 2.88x | Full-bodied bullish | Flat / fading | 0.013% / -0.050% / -0.044% | Weak move without breakout | 71.0% | 0.0% | 29.0% | 1.34x | 0.013% / 0.107% |
| 2025-04-13 16:45 | 4.21x | Bearish pin-bar / upper rejection | Flat / fading | 0.063% / 0.075% / 0.038% | Weak move without breakout | 4.2% | 62.5% | 33.3% | 1.73x | 0.125% / 0.031% |
| 2025-04-13 17:00 | 3.04x | Small-body bullish | Reversal | 0.013% / -0.013% / -0.094% | Liquidity sweep / reversal | 24.0% | 40.0% | 36.0% | 1.70x | 0.025% / 0.113% |
| 2025-04-14 07:00 | 11.35x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.277% / -0.327% / -0.365% | True breakout | 41.1% | 17.0% | 42.0% | 7.69x | 0.566% / 0.013% |
| 2025-04-14 07:30 | 2.67x | Bullish pin-bar / lower rejection | Reversal | 0.114% / -0.038% / 0.019% | Liquidity sweep / reversal | 22.6% | 5.7% | 71.7% | 2.07x | 0.170% / 0.164% |
| 2025-04-14 09:00 | 2.68x | Full-bodied bearish | Impulse / continuation | 0.006% / -0.013% / -0.342% | True breakout | 64.4% | 11.0% | 24.7% | 2.27x | 0.462% / 0.228% |
| 2025-04-14 10:00 | 4.72x | Full-bodied bearish | Flat / fading | 0.006% / 0.273% / 0.210% | Weak move without breakout | 60.0% | 20.0% | 20.0% | 2.15x | 0.064% / 0.496% |
| 2025-04-14 11:45 | 2.14x | Full-bodied bullish | Flat / fading | -0.057% / -0.176% / -0.076% | Weak move without breakout | 64.0% | 22.7% | 13.3% | 1.49x | 0.120% / 0.296% |
| 2025-04-14 15:45 | 2.64x | Full-bodied bearish | Impulse / continuation | -0.051% / 0.006% / -0.446% | True breakout | 64.1% | 12.0% | 23.9% | 2.75x | 0.592% / 0.140% |
| 2025-04-14 20:00 | 2.61x | Full-bodied bearish | Flat / fading | 0.162% / 0.368% / 0.110% | Weak move without breakout | 76.6% | 23.4% | 0.0% | 2.43x | 0.136% / 0.459% |
| 2025-04-15 09:15 | 7.47x | Full-bodied bullish | Flat / fading | -0.058% / -0.198% / 0.115% | Weak move without breakout | 65.3% | 28.5% | 6.3% | 4.79x | 0.493% / 0.397% |
| 2025-04-15 10:00 | 4.58x | Full-bodied bullish | Reversal | -0.102% / -0.077% / -0.556% | Liquidity sweep / reversal | 65.3% | 13.3% | 21.4% | 1.50x | 0.275% / 0.664% |
| 2025-04-15 10:15 | 2.87x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.026% / -0.301% / -0.550% | True breakout | 25.0% | 67.2% | 7.8% | 0.93x | 0.716% / 0.185% |
| 2025-04-15 17:00 | 2.88x | Full-bodied bullish | Reversal | -0.381% / -0.470% / -0.623% | Liquidity sweep / reversal | 67.8% | 25.4% | 6.8% | 2.29x | 0.038% / 0.686% |
| 2025-04-16 07:00 | 3.94x | Full-bodied bearish | Reversal | 0.064% / 0.115% / 0.198% | Liquidity sweep / reversal | 80.0% | 11.1% | 8.9% | 1.55x | 0.000% / 0.256% |
| 2025-04-16 09:00 | 2.84x | Bullish pin-bar / lower rejection | Reversal | -0.198% / -0.179% / -0.237% | Liquidity sweep / reversal | 15.9% | 22.2% | 61.9% | 1.99x | 0.064% / 0.377% |
| 2025-04-16 10:00 | 3.47x | Bearish pin-bar / upper rejection | Flat / fading | 0.064% / 0.205% / -0.071% | Weak move without breakout | 27.9% | 48.8% | 23.3% | 1.14x | 0.282% / 0.135% |
| 2025-04-16 11:15 | 6.05x | Full-bodied bullish | Flat / fading | -0.026% / -0.160% / 0.045% | Weak move without breakout | 63.0% | 21.5% | 15.6% | 3.21x | 0.313% / 0.351% |
| 2025-04-16 11:30 | 2.80x | Bullish pin-bar / lower rejection | Reversal | -0.134% / -0.102% / 0.057% | Liquidity sweep / reversal | 12.5% | 25.0% | 62.5% | 0.96x | 0.326% / 0.338% |
| 2025-04-16 16:45 | 2.46x | Full-bodied bullish | Flat / fading | -0.263% / -0.445% / 0.232% | Weak move without breakout | 98.9% | 0.0% | 1.1% | 1.91x | 0.301% / 0.520% |
| 2025-04-16 17:00 | 2.22x | Small-body bearish | Reversal | -0.182% / 0.308% / 0.264% | Liquidity sweep / reversal | 56.0% | 4.0% | 40.0% | 1.43x | 0.258% / 0.685% |
| 2025-04-16 19:00 | 2.77x | Full-bodied bearish | Flat / fading | -0.044% / -0.101% / 0.038% | Weak move without breakout | 71.3% | 7.8% | 20.9% | 2.16x | 0.314% / 0.226% |
| 2025-04-17 07:00 | 3.02x | Full-bodied bullish | Impulse / continuation | -0.031% / 0.025% / 0.113% | True breakout | 77.0% | 23.0% | 0.0% | 1.95x | 0.301% / 0.107% |
| 2025-04-17 10:00 | 3.40x | Full-bodied bearish | Reversal | 0.057% / 0.321% / 0.346% | Liquidity sweep / reversal | 70.3% | 0.0% | 29.7% | 2.42x | 0.113% / 0.371% |
| 2025-04-17 11:15 | 6.70x | Full-bodied bullish | Flat / fading | -0.162% / 0.044% / -0.399% | Weak move without breakout | 75.4% | 16.2% | 8.5% | 3.97x | 0.162% / 0.449% |
| 2025-04-17 11:30 | 3.24x | Bearish pin-bar / upper rejection | Reversal | 0.206% / -0.175% / -0.025% | Liquidity sweep / reversal | 50.0% | 42.9% | 7.1% | 1.43x | 0.287% / 0.212% |
| 2025-04-17 17:00 | 2.83x | Full-bodied bearish | Impulse / continuation | -0.540% / -0.308% / -0.258% | True breakout | 76.5% | 16.7% | 6.9% | 3.06x | 0.879% / 0.113% |
| 2025-04-17 17:15 | 4.04x | Full-bodied bearish | Impulse / continuation | 0.234% / 0.057% / 0.417% | True breakout | 81.3% | 15.9% | 2.8% | 2.75x | 0.341% / 0.417% |
| 2025-04-17 17:30 | 3.95x | Small-body bullish | Flat / fading | -0.176% / 0.050% / 0.120% | Weak move without breakout | 42.9% | 26.4% | 30.8% | 2.11x | 0.265% / 0.573% |
| 2025-04-17 18:00 | 2.64x | Bullish pin-bar / lower rejection | Flat / fading | 0.132% / 0.069% / -0.057% | Weak move without breakout | 30.0% | 17.5% | 52.5% | 2.33x | 0.233% / 0.283% |
| 2025-04-17 20:45 | 4.71x | Bearish pin-bar / upper rejection | Flat / fading | -0.063% / 0.381% / 0.669% | Weak move without breakout | 58.3% | 40.6% | 1.1% | 2.95x | 0.738% / 0.238% |
| 2025-04-17 21:00 | 2.75x | Bearish pin-bar / upper rejection | Reversal | 0.444% / 0.382% / 0.382% | Liquidity sweep / reversal | 7.2% | 72.5% | 20.3% | 2.00x | 0.025% / 0.801% |
| 2025-04-18 07:00 | 3.32x | Bullish pin-bar / lower rejection | Reversal | -0.163% / -0.044% / -0.176% | Liquidity sweep / reversal | 4.7% | 27.5% | 67.8% | 2.05x | 0.094% / 0.383% |
| 2025-04-18 12:45 | 2.84x | Full-bodied bearish | Impulse / continuation | -0.178% / -0.210% / -0.248% | True breakout | 65.6% | 21.1% | 13.3% | 1.73x | 0.515% / 0.248% |
| 2025-04-18 16:00 | 4.23x | Bearish pin-bar / upper rejection | Flat / fading | 0.279% / 0.203% / 0.203% | Position building in range | 51.8% | 46.9% | 1.3% | 3.54x | 0.660% / 0.165% |
| 2025-04-21 07:00 | 4.28x | Bullish pin-bar / lower rejection | Flat / fading | 0.050% / -0.095% / 0.095% | Position building in range | 21.2% | 24.7% | 54.1% | 1.98x | 0.101% / 0.214% |
| 2025-04-21 10:00 | 7.12x | Full-bodied bullish | Impulse / continuation | -0.082% / 0.314% / 0.195% | True breakout | 60.8% | 26.8% | 12.4% | 2.77x | 0.559% / 0.339% |
| 2025-04-21 10:15 | 4.16x | Bullish pin-bar / lower rejection | Reversal | 0.396% / 0.233% / 0.478% | Liquidity sweep / reversal | 23.2% | 3.6% | 73.2% | 1.43x | 0.063% / 0.641% |
| 2025-04-21 10:30 | 7.75x | Small-body bullish | Flat / fading | -0.163% / -0.119% / 0.081% | Position building in range | 58.9% | 34.8% | 6.2% | 3.20x | 0.232% / 0.225% |
| 2025-04-21 13:15 | 3.18x | Bearish pin-bar / upper rejection | Flat / fading | -0.106% / 0.006% / -0.019% | Weak move without breakout | 29.7% | 67.2% | 3.1% | 1.14x | 0.243% / 0.230% |
| 2025-04-21 19:30 | 3.14x | Full-bodied bullish | Flat / fading | -0.062% / -0.142% / -0.303% | Position building in range | 61.3% | 38.7% | 0.0% | 2.88x | 0.037% / 0.322% |
| 2025-04-22 10:00 | 8.29x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.062% / 0.049% / -0.284% | True breakout | 39.1% | 46.4% | 14.5% | 3.21x | 0.327% / 0.142% |
| 2025-04-22 16:15 | 2.83x | Full-bodied bullish | Flat / fading | -0.080% / 0.074% / 0.080% | Weak move without breakout | 62.7% | 27.5% | 9.8% | 1.36x | 0.229% / 0.198% |
| 2025-04-22 18:00 | 2.85x | Bearish pin-bar / upper rejection | Reversal | 0.160% / 0.080% / 0.234% | Liquidity sweep / reversal | 5.7% | 86.8% | 7.5% | 1.36x | 0.043% / 0.327% |
| 2025-04-22 20:30 | 6.22x | Small-body bullish | Impulse / continuation | 0.252% / 0.730% / 0.442% | True breakout | 54.2% | 38.7% | 7.1% | 3.89x | 1.331% / 0.061% |
| 2025-04-22 20:45 | 2.99x | Full-bodied bullish | Impulse / continuation | 0.477% / 0.845% / -0.086% | True breakout | 68.3% | 15.0% | 16.7% | 1.24x | 1.077% / 0.208% |
| 2025-04-22 21:00 | 4.79x | Bearish pin-bar / upper rejection | Reversal | 0.365% / -0.286% / -0.274% | Liquidity sweep / reversal | 51.7% | 46.9% | 1.4% | 2.85x | 0.597% / 0.682% |
| 2025-04-23 09:00 | 2.64x | Full-bodied bearish | Impulse / continuation | -0.210% / -0.118% / -0.229% | True breakout | 86.7% | 4.4% | 8.8% | 2.72x | 0.464% / 0.173% |
| 2025-04-23 10:15 | 4.20x | Full-bodied bearish | Impulse / continuation | -0.662% / -0.449% / -0.231% | True breakout | 64.2% | 12.7% | 23.0% | 2.78x | 0.849% / -0.025% |
| 2025-04-23 10:30 | 3.96x | Full-bodied bearish | Reversal | 0.214% / 0.308% / 0.704% | Liquidity sweep / reversal | 81.7% | 7.0% | 11.3% | 1.67x | 0.188% / 0.704% |
| 2025-04-23 12:30 | 2.56x | Bullish pin-bar / lower rejection | Reversal | 0.269% / 0.257% / 0.808% | Liquidity sweep / reversal | 57.6% | 0.0% | 42.4% | 2.01x | 0.182% / 1.102% |
| 2025-04-23 19:00 | 2.52x | Small-body bearish | Reversal | -0.099% / 0.410% / 0.708% | Liquidity sweep / reversal | 33.7% | 30.0% | 36.3% | 1.58x | 0.273% / 1.155% |
| 2025-04-23 19:30 | 4.41x | Full-bodied bullish | Impulse / continuation | 0.025% / 0.297% / 0.161% | True breakout | 83.8% | 9.5% | 6.7% | 2.06x | 0.742% / 0.229% |
| 2025-04-23 20:00 | 3.91x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / -0.136% / -0.031% | Weak move without breakout | 37.9% | 62.1% | 0.0% | 2.11x | 0.074% / 0.321% |
| 2025-04-24 10:00 | 3.26x | Bullish pin-bar / lower rejection | Reversal | 0.180% / 0.099% / -0.198% | Liquidity sweep / reversal | 13.7% | 37.3% | 49.0% | 1.70x | 0.248% / 0.242% |
| 2025-04-24 10:30 | 2.93x | Small-body bearish | Impulse / continuation | 0.056% / -0.297% / -0.161% | True breakout | 43.3% | 30.0% | 26.7% | 0.87x | 0.341% / 0.124% |
| 2025-04-24 11:00 | 3.57x | Full-bodied bearish | Reversal | 0.180% / 0.137% / 0.323% | Liquidity sweep / reversal | 86.4% | 3.0% | 10.6% | 2.19x | 0.012% / 0.509% |
| 2025-04-24 12:45 | 2.84x | Full-bodied bullish | Flat / fading | -0.049% / -0.099% / -0.074% | Weak move without breakout | 72.3% | 1.5% | 26.2% | 1.64x | 0.037% / 0.148% |
| 2025-04-25 07:00 | 3.54x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.124% / 0.118% / 0.347% | True breakout | 34.1% | 63.6% | 2.3% | 1.84x | 0.354% / -0.031% |
| 2025-04-25 09:00 | 7.19x | Full-bodied bullish | Impulse / continuation | -0.136% / -0.179% / 0.160% | True breakout | 75.6% | 0.0% | 24.4% | 2.06x | 0.179% / 0.259% |
| 2025-04-25 09:15 | 3.63x | Bearish pin-bar / upper rejection | Reversal | -0.043% / 0.037% / 0.191% | Liquidity sweep / reversal | 48.9% | 42.2% | 8.9% | 1.88x | 0.123% / 0.327% |
| 2025-04-25 10:00 | 4.76x | Full-bodied bullish | Reversal | -0.105% / -0.074% / -0.271% | Liquidity sweep / reversal | 62.7% | 4.5% | 32.8% | 2.35x | 0.031% / 0.320% |
| 2025-04-25 10:30 | 3.24x | Bearish pin-bar / upper rejection | Reversal | -0.135% / -0.197% / -0.148% | Liquidity sweep / reversal | 7.7% | 61.5% | 30.8% | 0.82x | 0.006% / 0.277% |
| 2025-04-25 12:30 | 5.73x | Bearish pin-bar / upper rejection | Flat / fading | 0.092% / 0.159% / 0.031% | Weak move without breakout | 57.7% | 42.3% | 0.0% | 3.50x | 0.411% / 0.601% |
| 2025-04-25 13:30 | 6.17x | Bullish pin-bar / lower rejection | Reversal | 0.086% / 0.159% / 0.558% | Liquidity sweep / reversal | 2.9% | 23.6% | 73.6% | 3.48x | 0.147% / 0.809% |
| 2025-04-26 10:00 | 3.31x | Full-bodied bullish | Impulse / continuation | 0.066% / 0.272% / 0.422% | True breakout | 69.6% | 26.1% | 4.3% | 3.79x | 0.477% / 0.084% |
| 2025-04-26 10:30 | 2.54x | Full-bodied bullish | Impulse / continuation | -0.054% / 0.150% / 0.638% | True breakout | 71.4% | 28.6% | 0.0% | 1.60x | 0.710% / 0.078% |
| 2025-04-26 11:45 | 2.53x | Bullish pin-bar / lower rejection | Flat / fading | -0.191% / -0.126% / -0.060% | Weak move without breakout | 25.9% | 22.2% | 51.9% | 1.39x | 0.257% / -0.012% |
| 2025-04-26 16:30 | 6.85x | Full-bodied bearish | Impulse / continuation | -0.030% / -0.139% / 0.103% | True breakout | 71.9% | 7.2% | 21.0% | 8.20x | 0.380% / 0.181% |
| 2025-04-26 16:45 | 4.74x | Bearish pin-bar / upper rejection | Reversal | -0.109% / -0.060% / -0.091% | Liquidity sweep / reversal | 1.4% | 49.3% | 49.3% | 2.26x | 0.350% / 0.175% |
| 2025-04-26 17:00 | 3.41x | Bullish pin-bar / lower rejection | Reversal | 0.048% / 0.242% / 0.145% | Liquidity sweep / reversal | 28.6% | 7.9% | 63.5% | 1.86x | 0.060% / 0.284% |
| 2025-04-27 13:45 | 3.62x | Small-body bearish | Impulse / continuation | -0.006% / -0.108% / -0.042% | True breakout | 48.0% | 12.0% | 40.0% | 2.76x | 0.175% / 0.048% |
| 2025-04-27 16:15 | 4.87x | Bearish pin-bar / upper rejection | Flat / fading | 0.042% / 0.054% / 0.090% | Weak move without breakout | 41.9% | 58.1% | 0.0% | 3.48x | 0.156% / 0.018% |
| 2025-04-28 07:00 | 13.60x | Bullish pin-bar / lower rejection | Flat / fading | -0.090% / -0.018% / 0.054% | Position building in range | 30.0% | 26.3% | 43.8% | 4.96x | 0.054% / 0.114% |
| 2025-04-28 08:30 | 2.94x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.217% / -0.277% / -0.223% | True breakout | 55.2% | 3.4% | 41.4% | 1.37x | 0.464% / 0.006% |
| 2025-04-28 08:45 | 4.38x | Small-body bearish | Flat / fading | -0.060% / -0.103% / 0.127% | Weak move without breakout | 59.6% | 5.3% | 35.1% | 2.62x | 0.248% / 0.260% |
| 2025-04-28 09:00 | 3.78x | Bullish pin-bar / lower rejection | Reversal | -0.042% / 0.054% / -0.109% | Liquidity sweep / reversal | 22.5% | 0.0% | 77.5% | 1.60x | 0.121% / 0.320% |
| 2025-04-28 10:00 | 3.41x | Full-bodied bearish | Impulse / continuation | -0.169% / -0.145% / 0.103% | True breakout | 100.0% | 0.0% | 0.0% | 1.67x | 0.375% / 0.188% |
| 2025-04-28 10:15 | 4.28x | Bullish pin-bar / lower rejection | Reversal | 0.024% / 0.048% / 0.133% | Liquidity sweep / reversal | 43.8% | 15.6% | 40.6% | 1.92x | 0.206% / 0.358% |
| 2025-04-28 13:15 | 4.36x | Full-bodied bearish | Reversal | 0.306% / 0.379% / 1.296% | Liquidity sweep / reversal | 69.9% | 8.4% | 21.7% | 1.93x | 0.043% / 1.840% |
| 2025-04-28 13:45 | 2.73x | Bearish pin-bar / upper rejection | Reversal | -0.140% / 0.914% / 0.938% | Liquidity sweep / reversal | 15.2% | 66.7% | 18.2% | 2.11x | 1.456% / 0.213% |
| 2025-04-28 14:15 | 8.13x | Full-bodied bullish | Flat / fading | 0.121% / 0.024% / 0.012% | Position building in range | 64.7% | 33.5% | 1.9% | 5.44x | 0.362% / 0.272% |
| 2025-04-28 21:45 | 2.99x | Full-bodied bearish | Flat / fading | -0.031% / 0.116% / 0.092% | Weak move without breakout | 75.4% | 4.9% | 19.7% | 2.17x | 0.122% / 0.256% |
| 2025-04-29 09:00 | 3.32x | Full-bodied bearish | Flat / fading | 0.134% / 0.300% / 0.067% | Position building in range | 93.5% | 0.0% | 6.5% | 2.64x | 0.006% / 0.336% |
| 2025-04-29 12:15 | 3.72x | Small-body bearish | Impulse / continuation | -0.244% / -0.128% / -0.220% | True breakout | 56.5% | 17.4% | 26.1% | 0.67x | 0.427% / 0.067% |
| 2025-04-29 12:30 | 5.07x | Small-body bearish | Flat / fading | 0.116% / -0.067% / -0.024% | Position building in range | 49.4% | 13.6% | 37.0% | 2.35x | 0.128% / 0.184% |
| 2025-04-29 17:45 | 3.25x | Small-body bearish | Impulse / continuation | -0.166% / -0.123% / -0.055% | True breakout | 48.1% | 29.6% | 22.2% | 2.08x | 0.356% / 0.049% |
| 2025-04-29 18:00 | 3.68x | Bullish pin-bar / lower rejection | Reversal | 0.043% / 0.117% / 0.190% | Liquidity sweep / reversal | 36.4% | 16.7% | 47.0% | 1.53x | 0.037% / 0.258% |
| 2025-04-29 19:30 | 3.63x | Full-bodied bearish | Impulse / continuation | -0.192% / -0.211% / -0.050% | True breakout | 72.5% | 15.5% | 12.0% | 3.12x | 0.496% / 0.223% |
| 2025-04-29 19:45 | 2.60x | Small-body bearish | Reversal | -0.019% / 0.323% / 0.193% | Liquidity sweep / reversal | 29.6% | 38.8% | 31.6% | 1.89x | 0.304% / 0.404% |
| 2025-04-30 07:30 | 2.73x | Full-bodied bearish | Impulse / continuation | -0.640% / -0.307% / -0.038% | True breakout | 73.4% | 0.0% | 26.6% | 5.68x | 0.878% / 0.125% |
| 2025-04-30 07:45 | 3.49x | Full-bodied bearish | Reversal | 0.334% / 0.461% / 0.701% | Liquidity sweep / reversal | 72.0% | 1.4% | 26.6% | 3.40x | 0.019% / 0.795% |
| 2025-04-30 09:00 | 4.07x | Bearish pin-bar / upper rejection | Reversal | -0.038% / -0.113% / -0.251% | Liquidity sweep / reversal | 8.4% | 86.7% | 4.8% | 1.54x | 0.238% / 0.482% |
| 2025-04-30 10:00 | 3.53x | Bullish pin-bar / lower rejection | Reversal | -0.138% / 0.138% / 0.006% | Liquidity sweep / reversal | 51.4% | 8.1% | 40.5% | 1.11x | 0.339% / 0.521% |
| 2025-04-30 12:15 | 2.55x | Small-body bearish | Reversal | 0.271% / 0.442% / 0.385% | Liquidity sweep / reversal | 46.4% | 18.8% | 34.8% | 1.19x | 0.044% / 0.845% |
| 2025-04-30 15:00 | 2.73x | Small-body bullish | Reversal | -0.093% / -0.093% / -0.684% | Liquidity sweep / reversal | 40.8% | 38.8% | 20.4% | 1.82x | 0.118% / 0.834% |
| 2025-04-30 15:45 | 2.65x | Small-body bearish | Flat / fading | -0.206% / -0.106% / -0.419% | Weak move without breakout | 50.8% | 25.4% | 23.8% | 2.12x | 0.456% / 0.138% |
| 2025-04-30 19:00 | 2.95x | Full-bodied bearish | Flat / fading | 0.013% / 0.228% / 0.272% | Position building in range | 73.5% | 5.3% | 21.2% | 2.50x | 0.177% / 0.405% |
| 2025-04-30 22:30 | 2.82x | Bearish pin-bar / upper rejection | Flat / fading | 0.214% / 0.063% / -0.076% | Weak move without breakout | 44.7% | 50.0% | 5.3% | 2.34x | 0.334% / 0.170% |
| 2025-05-02 07:00 | 8.83x | Full-bodied bearish | Impulse / continuation | 0.198% / 0.045% / 0.217% | True breakout | 88.3% | 0.0% | 11.7% | 7.63x | 0.473% / 0.294% |
| 2025-05-02 10:00 | 3.50x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.237% / -0.423% / -0.686% | True breakout | 31.7% | 26.7% | 41.7% | 0.89x | 0.892% / 0.006% |
| 2025-05-02 10:30 | 2.60x | Small-body bearish | Flat / fading | -0.283% / -0.264% / -0.322% | Weak move without breakout | 37.8% | 28.4% | 33.8% | 1.05x | 0.593% / 0.013% |
| 2025-05-02 15:30 | 3.16x | Full-bodied bearish | Flat / fading | 0.208% / 0.188% / 0.032% | Position building in range | 69.1% | 23.6% | 7.3% | 1.72x | 0.000% / 0.285% |
| 2025-05-02 18:00 | 2.83x | Full-bodied bearish | Impulse / continuation | -0.352% / -0.482% / -0.398% | True breakout | 72.4% | 2.6% | 25.0% | 2.25x | 0.802% / 0.085% |
| 2025-05-02 18:15 | 3.29x | Small-body bearish | Impulse / continuation | -0.131% / -0.229% / -0.765% | True breakout | 56.7% | 12.4% | 30.9% | 2.84x | 0.785% / 0.164% |
| 2025-05-02 19:00 | 2.57x | Small-body bullish | Reversal | -0.720% / -0.347% / -0.517% | Liquidity sweep / reversal | 29.8% | 34.0% | 36.2% | 2.42x | 0.092% / 0.739% |
| 2025-05-04 10:00 | 6.71x | Bearish pin-bar / upper rejection | Reversal | 0.040% / 0.178% / 0.145% | Liquidity sweep / reversal | 12.8% | 74.5% | 12.8% | 2.04x | 0.000% / 0.237% |
| 2025-05-04 10:30 | 2.89x | Full-bodied bullish | Flat / fading | -0.079% / -0.033% / 0.000% | Position building in range | 62.9% | 25.7% | 11.4% | 1.40x | 0.059% / 0.138% |
| 2025-05-04 12:00 | 4.27x | Bearish pin-bar / upper rejection | Flat / fading | 0.079% / -0.026% / 0.013% | Weak move without breakout | 56.2% | 43.8% | 0.0% | 1.98x | 0.157% / 0.059% |
| 2025-05-04 12:15 | 2.91x | Bearish pin-bar / upper rejection | Reversal | -0.105% / -0.079% / -0.125% | Liquidity sweep / reversal | 44.4% | 44.4% | 11.1% | 1.01x | 0.046% / 0.138% |
| 2025-05-04 16:30 | 5.47x | Bullish pin-bar / lower rejection | Flat / fading | -0.151% / 0.046% / 0.020% | Weak move without breakout | 50.0% | 6.0% | 44.0% | 4.36x | 0.290% / 0.125% |
| 2025-05-05 07:00 | 8.99x | Small-body bearish | Impulse / continuation | -0.258% / -0.363% / -0.172% | True breakout | 56.6% | 14.1% | 29.3% | 3.32x | 0.621% / 0.092% |
| 2025-05-05 07:45 | 2.80x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.159% / 0.212% / 0.179% | True breakout | 7.0% | 22.8% | 70.2% | 1.41x | 0.358% / 0.079% |
| 2025-05-05 09:00 | 2.61x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.179% / 0.358% | Liquidity sweep / reversal | 42.4% | 7.6% | 50.0% | 1.67x | 0.007% / 0.576% |
| 2025-05-05 10:00 | 3.92x | Small-body bullish | Reversal | 0.026% / -0.244% / -0.145% | Liquidity sweep / reversal | 36.8% | 37.9% | 25.3% | 2.06x | 0.211% / 0.442% |
| 2025-05-05 13:45 | 3.23x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.212% / -0.292% / -0.571% | True breakout | 47.7% | 1.5% | 50.8% | 1.50x | 0.717% / 0.113% |
| 2025-05-05 14:00 | 2.41x | Small-body bearish | Impulse / continuation | -0.080% / -0.047% / 0.020% | True breakout | 39.5% | 25.0% | 35.5% | 1.71x | 0.506% / 0.100% |
| 2025-05-05 14:45 | 2.32x | Full-bodied bearish | Reversal | 0.381% / 0.314% / -0.094% | Liquidity sweep / reversal | 68.1% | 0.0% | 31.9% | 1.56x | 0.274% / 0.387% |
| 2025-05-05 16:30 | 2.32x | Bullish pin-bar / lower rejection | Reversal | -0.208% / -0.590% / -1.146% | Liquidity sweep / reversal | 19.1% | 12.8% | 68.1% | 0.93x | 0.007% / 1.287% |
| 2025-05-05 17:00 | 2.40x | Full-bodied bearish | Impulse / continuation | -0.324% / -0.560% / -0.944% | True breakout | 70.4% | 28.4% | 1.2% | 1.65x | 1.389% / -0.007% |
| 2025-05-05 17:15 | 2.70x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.237% / -0.264% / -0.717% | True breakout | 58.8% | 0.0% | 41.2% | 1.54x | 1.069% / -0.014% |
| 2025-05-05 18:00 | 2.84x | Bullish pin-bar / lower rejection | Flat / fading | -0.095% / 0.286% / -0.585% | Weak move without breakout | 43.8% | 1.7% | 54.5% | 2.26x | 0.585% / 0.347% |
| 2025-05-05 18:15 | 2.18x | Bullish pin-bar / lower rejection | Reversal | 0.381% / 0.225% / 0.054% | Liquidity sweep / reversal | 15.7% | 24.1% | 60.2% | 1.38x | 0.511% / 0.443% |
| 2025-05-06 09:00 | 2.77x | Small-body bearish | Impulse -> reversal | -0.430% / -0.089% / 0.533% | False breakout | 57.6% | 21.2% | 21.2% | 1.97x | 0.608% / 0.621% |
| 2025-05-06 09:15 | 4.63x | Full-bodied bearish | Reversal | 0.343% / 0.535% / 1.372% | Liquidity sweep / reversal | 70.8% | 0.0% | 29.2% | 2.03x | 0.007% / 1.495% |
| 2025-05-06 10:00 | 3.69x | Full-bodied bullish | Impulse / continuation | 0.401% / 0.971% / 1.379% | True breakout | 82.9% | 17.1% | 0.0% | 1.36x | 1.488% / 0.217% |
| 2025-05-06 10:30 | 2.93x | Small-body bullish | Flat / fading | -0.256% / 0.404% / 0.067% | Weak move without breakout | 58.6% | 19.3% | 22.1% | 2.07x | 0.525% / 0.377% |
| 2025-05-06 16:00 | 2.57x | Bearish pin-bar / upper rejection | Flat / fading | 0.066% / 0.139% / 0.080% | Weak move without breakout | 34.0% | 66.0% | 0.0% | 0.89x | 0.239% / 0.080% |
| 2025-05-06 17:45 | 3.81x | Full-bodied bullish | Impulse / continuation | 0.118% / 0.053% / -0.131% | True breakout | 94.4% | 4.8% | 0.8% | 2.50x | 0.375% / 0.250% |
| 2025-05-06 18:00 | 2.65x | Bearish pin-bar / upper rejection | Reversal | -0.066% / -0.085% / -0.033% | Liquidity sweep / reversal | 37.1% | 62.9% | 0.0% | 1.12x | 0.092% / 0.630% |
| 2025-05-06 22:00 | 2.86x | Full-bodied bullish | Impulse / continuation | 0.214% / 0.182% / -0.182% | True breakout | 78.0% | 17.6% | 4.4% | 4.17x | 0.558% / 0.389% |
| 2025-05-07 10:00 | 3.69x | Full-bodied bearish | Reversal | 0.192% / 0.338% / 0.874% | Liquidity sweep / reversal | 68.9% | 1.6% | 29.5% | 1.81x | 0.007% / 0.947% |
| 2025-05-07 19:00 | 3.06x | Bearish pin-bar / upper rejection | Reversal | -0.098% / 0.117% / -0.431% | Liquidity sweep / reversal | 4.9% | 59.8% | 35.4% | 1.31x | 0.287% / 0.470% |
| 2025-05-08 09:00 | 3.38x | Full-bodied bullish | Impulse / continuation | -0.065% / -0.039% / 0.163% | True breakout | 75.3% | 0.0% | 24.7% | 2.23x | 0.390% / 0.390% |
| 2025-05-08 09:45 | 4.41x | Small-body bullish | Flat / fading | -0.052% / 0.143% / -0.097% | Weak move without breakout | 45.9% | 31.8% | 22.4% | 1.84x | 0.253% / 0.279% |
| 2025-05-08 10:00 | 3.95x | Bullish pin-bar / lower rejection | Reversal | 0.195% / 0.110% / -0.052% | Liquidity sweep / reversal | 10.6% | 36.4% | 53.0% | 1.32x | 0.201% / 0.305% |
| 2025-05-08 16:00 | 2.59x | Bearish pin-bar / upper rejection | Flat / fading | 0.052% / -0.039% / 0.026% | Position building in range | 45.2% | 46.6% | 8.2% | 1.71x | 0.131% / 0.209% |
| 2025-05-10 17:00 | 9.80x | Full-bodied bullish | Flat / fading | -0.039% / -0.072% / 0.026% | Position building in range | 61.5% | 34.6% | 3.8% | 3.60x | 0.026% / 0.078% |
| 2025-05-10 18:30 | 47.08x | Bullish pin-bar / lower rejection | Reversal | 0.275% / 2.407% / 2.702% | Liquidity sweep / reversal | 18.0% | 0.4% | 81.6% | 55.03x | 0.046% / 2.932% |
| 2025-05-10 18:45 | 3.93x | Small-body bullish | Impulse / continuation | 2.126% / 2.230% / 2.361% | True breakout | 55.6% | 22.2% | 22.2% | 1.39x | 2.649% / -1.714% |
| 2025-05-11 10:00 | 9.38x | Bullish pin-bar / lower rejection | Flat / fading | 0.186% / 0.128% / 0.409% | Weak move without breakout | 8.4% | 44.8% | 46.9% | 1.98x | 0.601% / 0.115% |
| 2025-05-11 10:15 | 3.58x | Full-bodied bullish | Flat / fading | -0.057% / 0.000% / 0.217% | Weak move without breakout | 65.9% | 22.7% | 11.4% | 0.54x | 0.415% / 0.300% |
| 2025-05-11 10:30 | 2.61x | Bullish pin-bar / lower rejection | Reversal | 0.058% / 0.281% / 0.147% | Liquidity sweep / reversal | 15.8% | 17.5% | 66.7% | 0.68x | 0.115% / 0.473% |
| 2025-05-11 15:45 | 6.47x | Full-bodied bearish | Flat / fading | 0.103% / 0.180% / 0.264% | Position building in range | 65.3% | 0.0% | 34.7% | 6.74x | 0.045% / 0.264% |
| 2025-05-12 07:00 | 6.94x | Full-bodied bearish | Reversal | 0.485% / 0.599% / 0.497% | Liquidity sweep / reversal | 61.6% | 32.9% | 5.5% | 1.48x | -0.019% / 0.663% |
| 2025-05-12 08:15 | 3.03x | Full-bodied bearish | Flat / fading | -0.032% / -0.057% / 0.000% | Weak move without breakout | 65.5% | 1.7% | 32.8% | 1.10x | 0.127% / 0.305% |
| 2025-05-12 09:00 | 3.14x | Bearish pin-bar / upper rejection | Flat / fading | -0.045% / -0.076% / 0.038% | Weak move without breakout | 24.6% | 67.2% | 8.2% | 1.15x | 0.273% / 0.159% |
| 2025-05-12 17:30 | 2.84x | Full-bodied bullish | Flat / fading | 0.025% / 0.057% / 0.025% | Weak move without breakout | 65.3% | 28.0% | 6.7% | 2.28x | 0.152% / 0.133% |
| 2025-05-12 20:15 | 3.85x | Bearish pin-bar / upper rejection | Flat / fading | 0.038% / -0.013% / -0.209% | Position building in range | 56.2% | 40.0% | 3.8% | 2.87x | 0.063% / 0.209% |
| 2025-05-13 07:00 | 3.37x | Bullish pin-bar / lower rejection | Reversal | 0.044% / 0.165% / 0.297% | Liquidity sweep / reversal | 31.1% | 11.1% | 57.8% | 2.27x | 0.025% / 0.418% |
| 2025-05-13 09:45 | 2.92x | Bullish pin-bar / lower rejection | Flat / fading | -0.082% / -0.139% / -0.032% | Weak move without breakout | 25.0% | 10.0% | 65.0% | 0.78x | 0.183% / 0.101% |
| 2025-05-13 10:00 | 5.68x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.057% / 0.006% / -0.221% | True breakout | 30.0% | 42.5% | 27.5% | 1.61x | 0.309% / 0.082% |
| 2025-05-13 11:00 | 3.17x | Full-bodied bearish | Impulse / continuation | -0.120% / -0.063% / -0.342% | True breakout | 72.9% | 3.4% | 23.7% | 2.44x | 0.437% / 0.089% |
| 2025-05-13 11:15 | 2.77x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.057% / -0.120% / -0.253% | True breakout | 48.6% | 40.5% | 10.8% | 1.44x | 0.329% / 0.101% |
| 2025-05-14 07:00 | 5.20x | Bearish pin-bar / upper rejection | Reversal | -0.006% / -0.076% / -0.082% | Liquidity sweep / reversal | 55.9% | 41.2% | 2.9% | 3.53x | 0.032% / 0.139% |
| 2025-05-14 10:00 | 3.33x | Full-bodied bearish | Impulse / continuation | 0.025% / 0.095% / 0.063% | True breakout | 62.1% | 34.5% | 3.4% | 2.00x | 0.165% / 0.209% |
| 2025-05-14 10:15 | 4.94x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.070% / 0.057% / 0.133% | True breakout | 13.2% | 21.1% | 65.8% | 2.38x | 0.215% / 0.038% |
| 2025-05-14 11:15 | 3.36x | Small-body bullish | Reversal | -0.051% / -0.051% / -0.063% | Liquidity sweep / reversal | 40.0% | 37.1% | 22.9% | 2.00x | 0.019% / 0.133% |
| 2025-05-14 15:15 | 5.48x | Small-body bullish | Flat / fading | -0.076% / 0.006% / -0.032% | Position building in range | 37.1% | 25.7% | 37.1% | 2.78x | 0.050% / 0.120% |
| 2025-05-14 16:30 | 11.65x | Full-bodied bullish | Flat / fading | -0.063% / -0.126% / -0.257% | Position building in range | 63.6% | 35.7% | 0.8% | 7.82x | 0.094% / 0.320% |
| 2025-05-14 16:45 | 3.25x | Bullish pin-bar / lower rejection | Flat / fading | -0.063% / -0.119% / -0.207% | Weak move without breakout | 25.9% | 20.4% | 53.7% | 2.15x | 0.276% / 0.075% |
| 2025-05-14 22:45 | 7.37x | Small-body bearish | Impulse / continuation | -0.299% / -0.776% / -1.895% | True breakout | 58.1% | 23.7% | 18.1% | 5.66x | 1.946% / 0.159% |
| 2025-05-14 23:00 | 5.94x | Small-body bearish | Impulse / continuation | -0.478% / -0.855% / -1.627% | True breakout | 49.4% | 33.3% | 17.2% | 2.32x | 1.652% / 0.070% |
| 2025-05-14 23:30 | 2.60x | Full-bodied bearish | Impulse -> reversal | -0.753% / -0.779% / 0.386% | False breakout | 96.6% | 3.4% | 0.0% | 1.30x | 0.804% / 0.579% |
| 2025-05-15 07:00 | 5.48x | Full-bodied bullish | Flat / fading | -0.019% / 0.083% / -0.122% | Weak move without breakout | 93.0% | 6.5% | 0.5% | 3.76x | 0.179% / 0.237% |
| 2025-05-16 07:00 | 5.66x | Full-bodied bullish | Flat / fading | -0.091% / -0.104% / -0.181% | Position building in range | 62.0% | 17.4% | 20.7% | 3.00x | 0.006% / 0.214% |
| 2025-05-16 10:30 | 3.35x | Bullish pin-bar / lower rejection | Flat / fading | 0.039% / 0.130% / 0.084% | Weak move without breakout | 52.0% | 0.0% | 48.0% | 2.12x | 0.026% / 0.208% |
| 2025-05-16 13:15 | 3.01x | Small-body bearish | Impulse / continuation | 0.039% / -0.058% / 0.032% | True breakout | 47.2% | 22.2% | 30.6% | 1.57x | 0.468% / 0.117% |
| 2025-05-16 14:00 | 3.65x | Bullish pin-bar / lower rejection | Reversal | 0.221% / 0.137% / -0.065% | Liquidity sweep / reversal | 31.7% | 0.0% | 68.3% | 2.54x | 0.273% / 0.351% |
| 2025-05-16 15:15 | 16.96x | Full-bodied bearish | Impulse / continuation | 0.184% / -0.527% / 0.231% | True breakout | 74.5% | 0.0% | 25.5% | 7.04x | 1.318% / 0.270% |
| 2025-05-16 15:30 | 2.72x | Bullish pin-bar / lower rejection | Reversal | -0.710% / -1.243% / 1.230% | Liquidity sweep / reversal | 37.1% | 21.0% | 41.9% | 1.22x | 1.545% / 1.499% |
| 2025-05-16 15:45 | 3.31x | Full-bodied bearish | Impulse -> reversal | -0.536% / 0.762% / 2.192% | False breakout | 70.1% | 1.9% | 27.9% | 2.88x | 0.795% / 2.424% |
| 2025-05-16 16:00 | 3.84x | Full-bodied bearish | Reversal | 1.305% / 2.504% / 2.730% | Liquidity sweep / reversal | 69.8% | 12.9% | 17.2% | 1.83x | 0.260% / 3.043% |
| 2025-05-16 16:15 | 3.89x | Full-bodied bullish | Impulse / continuation | 1.183% / 1.420% / 1.255% | True breakout | 84.3% | 0.4% | 15.3% | 3.34x | 1.716% / 0.289% |
| 2025-05-16 16:30 | 5.88x | Full-bodied bullish | Flat / fading | 0.234% / 0.221% / -0.136% | Weak move without breakout | 66.2% | 17.6% | 16.2% | 3.14x | 0.526% / 0.208% |
| 2025-05-16 23:00 | 2.90x | Small-body bearish | Reversal | -0.020% / -0.026% / 0.156% | Liquidity sweep / reversal | 40.8% | 28.6% | 30.6% | 2.58x | 0.169% / 0.156% |
| 2025-05-17 15:45 | 3.25x | Bullish pin-bar / lower rejection | Reversal | -0.032% / -0.045% / -0.058% | Liquidity sweep / reversal | 35.0% | 20.0% | 45.0% | 2.06x | -0.006% / 0.078% |
| 2025-05-17 17:45 | 6.50x | Full-bodied bullish | Impulse / continuation | 0.738% / 0.784% / 0.881% | True breakout | 75.7% | 24.3% | 0.0% | 5.13x | 1.030% / 0.071% |
| 2025-05-17 18:00 | 34.32x | Full-bodied bullish | Impulse / continuation | 0.045% / 0.084% / 0.939% | True breakout | 74.0% | 18.8% | 7.1% | 15.97x | 0.939% / 0.141% |
| 2025-05-17 18:15 | 7.05x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.039% / 0.096% / 0.996% | True breakout | 10.4% | 56.7% | 32.8% | 3.29x | 1.170% / 0.045% |
| 2025-05-18 10:00 | 3.71x | Small-body bullish | Flat / fading | -0.095% / 0.051% / 0.115% | Position building in range | 23.2% | 39.1% | 37.7% | 2.01x | 0.115% / 0.159% |
| 2025-05-18 18:45 | 3.32x | Small-body bullish | Reversal | 0.006% / -0.261% / -0.146% | Liquidity sweep / reversal | 30.8% | 38.5% | 30.8% | 1.34x | 0.006% / 0.267% |
| 2025-05-19 07:00 | 10.02x | Full-bodied bearish | Impulse / continuation | 0.127% / 0.115% / -0.427% | True breakout | 100.0% | 0.0% | 0.0% | 4.42x | 1.039% / 0.204% |
| 2025-05-19 07:45 | 12.11x | Bullish pin-bar / lower rejection | Flat / fading | -0.096% / -0.077% / -0.403% | Position building in range | 38.7% | 0.0% | 61.3% | 13.27x | 0.550% / 0.051% |
| 2025-05-19 08:45 | 3.11x | Full-bodied bearish | Flat / fading | 0.013% / 0.128% / 0.302% | Weak move without breakout | 71.3% | 4.3% | 24.5% | 3.16x | 0.238% / 0.308% |
| 2025-05-19 09:00 | 4.22x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.116% / 0.135% / 0.225% | True breakout | 5.2% | 32.8% | 62.1% | 1.62x | 0.372% / 0.096% |
| 2025-05-19 16:00 | 3.59x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.058% / -0.045% / -0.911% | True breakout | 49.3% | 5.6% | 45.1% | 3.32x | 1.013% / 0.045% |
| 2025-05-19 16:45 | 6.07x | Full-bodied bearish | Impulse / continuation | -0.464% / -0.019% / 0.000% | True breakout | 68.8% | 6.5% | 24.7% | 3.76x | 0.567% / 0.174% |
| 2025-05-19 17:00 | 4.90x | Full-bodied bearish | Reversal | 0.447% / 0.427% / 0.777% | Liquidity sweep / reversal | 63.5% | 22.6% | 13.9% | 3.78x | 0.058% / 1.146% |
| 2025-05-19 18:00 | 2.99x | Bearish pin-bar / upper rejection | Reversal | -0.507% / -0.250% / -0.128% | Liquidity sweep / reversal | 44.5% | 51.8% | 3.6% | 2.41x | 0.148% / 0.694% |
| 2025-05-19 19:30 | 2.54x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.309% / -0.348% / 0.103% | True breakout | 8.6% | 54.1% | 37.3% | 2.90x | 0.875% / 0.747% |
| 2025-05-19 19:45 | 7.95x | Bearish pin-bar / upper rejection | Reversal | -0.039% / 0.026% / 0.006% | Liquidity sweep / reversal | 18.7% | 46.4% | 34.9% | 3.50x | 0.168% / 0.736% |
| 2025-05-19 20:30 | 3.11x | Bearish pin-bar / upper rejection | Reversal | -0.405% / -0.373% / -0.965% | Liquidity sweep / reversal | 46.6% | 42.4% | 11.0% | 1.33x | 0.026% / 1.016% |
| 2025-05-20 10:00 | 5.95x | Full-bodied bearish | Impulse / continuation | -0.383% / -0.389% / -0.506% | True breakout | 70.8% | 1.4% | 27.8% | 2.08x | 0.772% / 0.065% |
| 2025-05-20 10:15 | 3.87x | Full-bodied bearish | Impulse / continuation | -0.007% / -0.300% / -0.254% | True breakout | 78.2% | 10.3% | 11.5% | 2.08x | 0.391% / 0.195% |
| 2025-05-20 10:30 | 2.91x | Bearish pin-bar / upper rejection | Flat / fading | -0.293% / -0.117% / -0.117% | Weak move without breakout | 2.4% | 53.7% | 43.9% | 0.99x | 0.384% / 0.202% |
| 2025-05-20 10:45 | 4.47x | Small-body bearish | Flat / fading | 0.176% / 0.046% / 0.085% | Position building in range | 50.0% | 34.4% | 15.6% | 2.32x | 0.033% / 0.229% |
| 2025-05-20 16:00 | 3.30x | Bullish pin-bar / lower rejection | Flat / fading | -0.046% / -0.039% / -0.085% | Position building in range | 32.4% | 21.6% | 45.9% | 3.64x | 0.104% / 0.221% |
| 2025-05-21 07:15 | 3.38x | Full-bodied bullish | Flat / fading | 0.072% / -0.163% / -0.234% | Weak move without breakout | 92.8% | 7.2% | 0.0% | 4.08x | 0.111% / 0.234% |
| 2025-05-21 07:30 | 2.54x | Small-body bullish | Reversal | -0.234% / -0.208% / -0.305% | Liquidity sweep / reversal | 50.0% | 23.1% | 26.9% | 1.30x | 0.013% / 0.338% |
| 2025-05-21 09:30 | 6.39x | Bearish pin-bar / upper rejection | Reversal | -0.182% / -0.436% / -0.384% | Liquidity sweep / reversal | 32.3% | 64.5% | 3.2% | 2.47x | 0.013% / 0.618% |
| 2025-05-21 10:00 | 3.99x | Small-body bearish | Flat / fading | -0.105% / 0.052% / -0.059% | Weak move without breakout | 48.8% | 35.0% | 16.2% | 2.61x | 0.183% / 0.131% |
| 2025-05-21 10:15 | 4.56x | Small-body bearish | Reversal | 0.157% / 0.065% / -0.033% | Liquidity sweep / reversal | 51.6% | 9.7% | 38.7% | 0.87x | 0.098% / 0.236% |
| 2025-05-21 11:00 | 2.61x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.078% / -0.105% / -0.556% | True breakout | 9.8% | 61.0% | 29.3% | 1.17x | 0.739% / 0.072% |
| 2025-05-21 12:15 | 2.33x | Bullish pin-bar / lower rejection | Flat / fading | -0.033% / 0.039% / -0.290% | Weak move without breakout | 23.3% | 33.3% | 43.3% | 1.41x | 0.342% / 0.158% |
| 2025-05-21 17:00 | 2.51x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.165% / -0.245% / -0.496% | True breakout | 52.9% | 1.4% | 45.7% | 1.94x | 0.529% / -0.013% |
| 2025-05-22 07:00 | 3.28x | Small-body bullish | Reversal | -0.046% / -0.544% / -1.100% | Liquidity sweep / reversal | 45.9% | 29.5% | 24.6% | 3.00x | 0.040% / 1.107% |
| 2025-05-22 07:30 | 2.80x | Full-bodied bearish | Impulse / continuation | -0.133% / -0.560% / -0.933% | True breakout | 95.0% | 5.0% | 0.0% | 3.53x | 0.993% / 0.127% |
| 2025-05-22 07:45 | 3.93x | Small-body bearish | Impulse / continuation | -0.427% / -0.307% / -0.641% | True breakout | 34.5% | 32.8% | 32.8% | 2.15x | 0.861% / 0.000% |
| 2025-05-22 08:00 | 4.05x | Full-bodied bearish | Impulse / continuation | 0.121% / -0.375% / -0.375% | True breakout | 98.5% | 0.0% | 1.5% | 2.16x | 0.436% / 0.121% |
| 2025-05-22 08:15 | 5.22x | Bullish pin-bar / lower rejection | Reversal | -0.495% / -0.335% / -0.910% | Liquidity sweep / reversal | 30.0% | 0.0% | 70.0% | 1.77x | 0.000% / 1.058% |
| 2025-05-22 08:30 | 2.77x | Full-bodied bearish | Impulse / continuation | 0.161% / 0.000% / -0.383% | True breakout | 89.2% | 0.0% | 10.8% | 2.27x | 0.565% / 0.168% |
| 2025-05-22 09:15 | 4.52x | Full-bodied bearish | Reversal | 0.034% / 0.432% / 1.527% | Liquidity sweep / reversal | 62.9% | 14.4% | 22.7% | 2.20x | 0.027% / 1.533% |
| 2025-05-22 09:30 | 3.10x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.398% / 0.918% / 1.972% | True breakout | 7.3% | 90.9% | 1.8% | 1.10x | 2.242% / 0.061% |
| 2025-05-22 10:00 | 9.44x | Full-bodied bullish | Impulse / continuation | 0.569% / 1.044% / 0.709% | True breakout | 65.8% | 29.9% | 4.3% | 2.05x | 1.312% / 0.013% |
| 2025-05-22 10:30 | 2.98x | Small-body bullish | Flat / fading | -0.364% / -0.331% / 0.033% | Position building in range | 51.1% | 28.8% | 20.1% | 2.09x | 0.099% / 0.596% |
| 2025-05-22 15:45 | 3.61x | Full-bodied bullish | Flat / fading | 0.157% / -0.164% / 0.118% | Weak move without breakout | 64.5% | 33.1% | 2.4% | 2.71x | 0.413% / 0.249% |
| 2025-05-22 17:45 | 4.18x | Bearish pin-bar / upper rejection | Reversal | 0.187% / -0.123% / -0.497% | Liquidity sweep / reversal | 35.7% | 58.7% | 5.6% | 1.75x | 0.200% / 0.497% |
| 2025-05-23 09:45 | 2.70x | Bullish pin-bar / lower rejection | Reversal | -0.130% / 0.195% / 0.319% | Liquidity sweep / reversal | 26.7% | 23.3% | 50.0% | 1.44x | 0.293% / 0.592% |
| 2025-05-23 10:00 | 3.04x | Bullish pin-bar / lower rejection | Reversal | 0.326% / 0.521% / 0.241% | Liquidity sweep / reversal | 42.6% | 4.3% | 53.2% | 1.08x | 0.020% / 0.723% |
| 2025-05-23 10:30 | 5.77x | Small-body bullish | Reversal | -0.071% / -0.279% / -0.207% | Liquidity sweep / reversal | 31.5% | 28.7% | 39.8% | 2.21x | 0.013% / 0.499% |
| 2025-05-23 23:30 | 2.58x | Bearish pin-bar / upper rejection | Reversal | 0.013% / 0.006% / -0.864% | Liquidity sweep / reversal | 22.2% | 44.4% | 33.3% | 1.37x | 0.045% / 0.883% |
| 2025-05-26 07:00 | 8.82x | Full-bodied bearish | Impulse / continuation | -0.144% / -0.242% / -0.262% | True breakout | 88.1% | 0.8% | 11.1% | 10.44x | 0.497% / 0.216% |
| 2025-05-26 07:15 | 3.04x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.098% / -0.223% / -0.458% | True breakout | 37.9% | 56.9% | 5.2% | 2.81x | 0.642% / 0.072% |
| 2025-05-26 07:30 | 4.59x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.125% / -0.020% / -0.249% | True breakout | 28.8% | 0.0% | 71.2% | 2.21x | 0.583% / 0.170% |
| 2025-05-26 07:45 | 2.83x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.105% / -0.236% / -0.026% | True breakout | 27.7% | 41.5% | 30.8% | 2.50x | 0.459% / 0.197% |
| 2025-05-26 08:15 | 2.65x | Full-bodied bearish | Flat / fading | 0.112% / 0.211% / 0.178% | Weak move without breakout | 62.7% | 3.6% | 33.7% | 2.56x | 0.224% / 0.329% |
| 2025-05-26 10:00 | 2.71x | Full-bodied bearish | Flat / fading | -0.106% / -0.086% / 0.198% | Weak move without breakout | 71.6% | 27.4% | 1.1% | 1.86x | 0.251% / 0.455% |
| 2025-05-26 10:15 | 2.86x | Bearish pin-bar / upper rejection | Reversal | 0.020% / 0.192% / 0.462% | Liquidity sweep / reversal | 25.0% | 42.6% | 32.4% | 1.20x | 0.092% / 0.562% |
| 2025-05-26 19:15 | 3.32x | Full-bodied bearish | Flat / fading | 0.153% / 0.146% / 0.338% | Position building in range | 68.1% | 12.1% | 19.8% | 2.68x | 0.033% / 0.404% |
| 2025-05-27 07:00 | 2.94x | Bullish pin-bar / lower rejection | Reversal | -0.535% / -0.614% / -0.806% | Liquidity sweep / reversal | 4.0% | 26.0% | 70.0% | 2.22x | 0.053% / 1.202% |
| 2025-05-27 07:15 | 2.62x | Full-bodied bearish | Impulse / continuation | -0.080% / -0.325% / 0.213% | True breakout | 87.9% | 9.9% | 2.2% | 3.66x | 0.671% / 0.286% |
| 2025-05-27 07:30 | 6.68x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.246% / -0.193% / 0.499% | False breakout | 18.7% | 9.3% | 72.0% | 2.58x | 0.592% / 0.499% |
| 2025-05-27 07:45 | 4.87x | Bullish pin-bar / lower rejection | Reversal | 0.053% / 0.540% / 0.620% | Liquidity sweep / reversal | 39.4% | 5.3% | 55.3% | 2.80x | 0.013% / 0.886% |
| 2025-05-27 09:45 | 3.25x | Full-bodied bullish | Flat / fading | 0.066% / -0.249% / 0.151% | Weak move without breakout | 73.9% | 21.7% | 4.3% | 1.24x | 0.177% / 0.472% |
| 2025-05-27 10:00 | 2.70x | Bullish pin-bar / lower rejection | Reversal | -0.314% / -0.327% / 0.131% | Liquidity sweep / reversal | 15.7% | 33.3% | 51.0% | 0.86x | 0.426% / 0.537% |
| 2025-05-27 11:00 | 2.34x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.307% / 0.719% / 0.883% | True breakout | 12.1% | 77.6% | 10.3% | 0.90x | 0.948% / 0.164% |
| 2025-05-27 11:30 | 2.66x | Small-body bullish | Flat / fading | -0.058% / 0.162% / -0.377% | Weak move without breakout | 53.4% | 27.6% | 19.0% | 1.88x | 0.227% / 0.416% |
| 2025-05-28 07:00 | 4.62x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.026% / 0.006% / 0.205% | True breakout | 41.4% | 41.4% | 17.2% | 2.75x | 0.443% / 0.083% |
| 2025-05-28 10:00 | 6.45x | Full-bodied bullish | Impulse / continuation | 0.249% / 0.332% / 0.446% | True breakout | 66.7% | 18.5% | 14.8% | 3.25x | 0.574% / 0.057% |
| 2025-05-28 10:15 | 3.71x | Full-bodied bullish | Flat / fading | 0.083% / -0.025% / -0.019% | Weak move without breakout | 62.9% | 22.6% | 14.5% | 1.56x | 0.324% / 0.102% |
| 2025-05-28 10:30 | 4.33x | Bearish pin-bar / upper rejection | Reversal | -0.108% / 0.114% / -0.013% | Liquidity sweep / reversal | 24.5% | 40.8% | 34.7% | 1.15x | 0.242% / 0.165% |
| 2025-05-28 12:30 | 2.48x | Full-bodied bullish | Flat / fading | -0.038% / -0.308% / 0.063% | Weak move without breakout | 82.3% | 8.9% | 8.9% | 1.52x | 0.365% / 0.636% |
| 2025-05-28 12:45 | 2.70x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.271% / -0.069% / 0.208% | False breakout | 12.8% | 63.8% | 23.4% | 0.87x | 0.598% / 0.403% |
| 2025-05-28 15:15 | 1.88x | Full-bodied bullish | Flat / fading | 0.063% / 0.025% / 0.125% | Weak move without breakout | 89.5% | 10.5% | 0.0% | 1.58x | 0.332% / 0.119% |
| 2025-05-28 19:15 | 3.36x | Full-bodied bullish | Flat / fading | -0.261% / -0.062% / -0.105% | Weak move without breakout | 97.4% | 2.6% | 0.0% | 2.18x | 0.081% / 0.298% |
| 2025-05-29 09:00 | 2.55x | Full-bodied bearish | Reversal | 0.369% / 0.194% / -0.188% | Liquidity sweep / reversal | 68.7% | 1.5% | 29.9% | 1.84x | 0.300% / 0.532% |
| 2025-05-29 10:00 | 2.89x | Full-bodied bearish | Flat / fading | 0.013% / 0.100% / 0.075% | Weak move without breakout | 67.6% | 5.9% | 26.5% | 1.47x | 0.176% / 0.232% |
| 2025-05-29 15:45 | 6.92x | Bullish pin-bar / lower rejection | Flat / fading | -0.312% / -0.243% / -0.337% | Weak move without breakout | 23.9% | 1.8% | 74.3% | 3.32x | 0.587% / 0.006% |
| 2025-05-30 10:00 | 3.55x | Bullish pin-bar / lower rejection | Flat / fading | -0.069% / 0.031% / -0.188% | Weak move without breakout | 16.7% | 39.6% | 43.7% | 1.28x | 0.357% / 0.050% |
| 2025-05-30 10:45 | 2.84x | Full-bodied bearish | Impulse / continuation | 0.170% / -0.289% / -0.025% | True breakout | 100.0% | 0.0% | 0.0% | 1.58x | 0.377% / 0.182% |
| 2025-05-30 11:15 | 2.63x | Full-bodied bearish | Reversal | 0.113% / 0.264% / 0.642% | Liquidity sweep / reversal | 83.9% | 0.0% | 16.1% | 2.38x | 0.063% / 0.768% |
| 2025-05-30 12:00 | 3.37x | Full-bodied bullish | Impulse / continuation | 0.025% / 0.006% / 0.401% | True breakout | 65.4% | 30.8% | 3.8% | 1.86x | 0.657% / 0.138% |
| 2025-05-30 12:30 | 2.72x | Bearish pin-bar / upper rejection | Reversal | 0.219% / 0.394% / 0.269% | Liquidity sweep / reversal | 5.6% | 51.9% | 42.6% | 1.18x | 0.038% / 0.651% |
| 2025-05-30 13:00 | 3.01x | Bearish pin-bar / upper rejection | Flat / fading | -0.112% / -0.125% / -0.025% | Position building in range | 43.4% | 53.9% | 2.6% | 1.57x | 0.112% / 0.193% |
| 2025-06-01 10:00 | 48.18x | Bullish pin-bar / lower rejection | Flat / fading | 0.038% / -0.164% / -0.138% | Position building in range | 18.6% | 0.2% | 81.2% | 61.89x | 0.504% / 0.063% |
| 2025-06-01 10:30 | 2.85x | Full-bodied bearish | Impulse / continuation | -0.227% / 0.025% / 0.000% | True breakout | 62.5% | 0.0% | 37.5% | 1.06x | 0.340% / 0.088% |
| 2025-06-01 10:45 | 3.42x | Full-bodied bearish | Reversal | 0.253% / 0.259% / 0.095% | Liquidity sweep / reversal | 66.7% | 0.0% | 33.3% | 1.32x | 0.082% / 0.316% |
| 2025-06-01 13:45 | 2.97x | Full-bodied bearish | Impulse / continuation | -0.458% / -0.789% / -0.789% | True breakout | 80.0% | 18.2% | 1.8% | 1.59x | 1.119% / 0.051% |
| 2025-06-01 14:00 | 6.10x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.332% / -0.600% / -0.505% | True breakout | 50.3% | 4.8% | 44.8% | 3.96x | 0.696% / 0.224% |
| 2025-06-01 14:15 | 3.33x | Full-bodied bearish | Impulse / continuation | -0.269% / 0.000% / 0.244% | True breakout | 64.0% | 33.7% | 2.2% | 2.04x | 0.365% / 0.308% |
| 2025-06-01 14:30 | 2.82x | Bearish pin-bar / upper rejection | Reversal | 0.270% / 0.096% / 0.469% | Liquidity sweep / reversal | 58.3% | 41.7% | 0.0% | 1.56x | 0.096% / 0.578% |
| 2025-06-01 14:45 | 3.46x | Small-body bullish | Flat / fading | -0.173% / 0.244% / 0.340% | Weak move without breakout | 52.5% | 35.0% | 12.5% | 1.71x | 0.359% / 0.365% |
| 2025-06-01 16:00 | 2.77x | Bearish pin-bar / upper rejection | Reversal | -0.089% / -0.210% / -0.057% | Liquidity sweep / reversal | 26.5% | 70.8% | 2.7% | 1.82x | 0.166% / 0.300% |
| 2025-06-02 07:00 | 2.64x | Full-bodied bullish | Impulse / continuation | 0.064% / 0.191% / 0.286% | True breakout | 67.4% | 1.1% | 31.5% | 3.75x | 0.356% / 0.222% |
| 2025-06-02 09:00 | 2.53x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / 0.158% / 0.374% | Weak move without breakout | 48.2% | 42.9% | 8.9% | 1.06x | 0.450% / 0.101% |
| 2025-06-02 10:00 | 3.44x | Small-body bullish | Flat / fading | -0.095% / 0.271% / 0.158% | Weak move without breakout | 45.6% | 17.6% | 36.8% | 1.25x | 0.360% / 0.221% |
| 2025-06-02 17:30 | 2.93x | Small-body bullish | Impulse / continuation | 0.025% / 0.308% / 0.439% | True breakout | 53.5% | 10.9% | 35.6% | 1.56x | 0.772% / 0.082% |
| 2025-06-02 17:45 | 2.79x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.282% / 0.320% / 0.483% | True breakout | 3.6% | 83.9% | 12.5% | 0.80x | 0.747% / 0.107% |
| 2025-06-02 18:15 | 2.48x | Bearish pin-bar / upper rejection | Flat / fading | 0.094% / 0.163% / 0.006% | Position building in range | 5.0% | 68.0% | 27.0% | 1.41x | 0.313% / 0.119% |
| 2025-06-03 07:00 | 3.69x | Full-bodied bullish | Impulse / continuation | 0.075% / 0.256% / 0.287% | True breakout | 63.1% | 26.2% | 10.7% | 3.70x | 0.325% / 0.006% |
| 2025-06-03 10:00 | 3.36x | Small-body bullish | Impulse / continuation | 0.605% / 0.387% / 0.530% | True breakout | 42.9% | 26.8% | 30.4% | 1.61x | 0.730% / 0.006% |
| 2025-06-03 10:15 | 6.31x | Full-bodied bullish | Flat / fading | -0.217% / -0.130% / -0.056% | Weak move without breakout | 88.3% | 11.7% | 0.0% | 2.93x | 0.124% / 0.260% |
| 2025-06-03 10:30 | 2.61x | Full-bodied bearish | Flat / fading | 0.087% / 0.143% / 0.087% | Weak move without breakout | 64.2% | 22.6% | 13.2% | 1.20x | 0.019% / 0.342% |
| 2025-06-03 11:00 | 2.53x | Bearish pin-bar / upper rejection | Flat / fading | 0.019% / -0.056% / 0.292% | Weak move without breakout | 18.4% | 65.3% | 16.3% | 1.17x | 0.323% / 0.105% |
| 2025-06-03 18:00 | 5.43x | Full-bodied bullish | Impulse / continuation | 0.025% / 0.241% / 0.364% | True breakout | 78.9% | 11.8% | 9.2% | 2.07x | 0.401% / 0.080% |
| 2025-06-04 07:00 | 4.35x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.067% / -0.104% / -0.288% | True breakout | 33.7% | 47.0% | 19.3% | 2.96x | 0.318% / 0.190% |
| 2025-06-04 09:45 | 3.72x | Full-bodied bullish | Impulse / continuation | 0.067% / 0.085% / 0.213% | True breakout | 97.4% | 0.0% | 2.6% | 0.82x | 0.358% / 0.134% |
| 2025-06-04 10:00 | 3.93x | Bullish pin-bar / lower rejection | Reversal | 0.018% / 0.182% / -0.103% | Liquidity sweep / reversal | 33.3% | 8.3% | 58.3% | 0.79x | 0.291% / 0.176% |
| 2025-06-04 10:15 | 3.03x | Bearish pin-bar / upper rejection | Reversal | 0.164% / 0.127% / 0.049% | Liquidity sweep / reversal | 3.1% | 65.6% | 31.2% | 0.69x | 0.273% / 0.194% |
| 2025-06-04 17:15 | 3.79x | Small-body bearish | Flat / fading | 0.280% / 0.055% / -0.043% | Weak move without breakout | 52.5% | 16.9% | 30.5% | 2.04x | 0.481% / 0.378% |
| 2025-06-05 09:15 | 2.72x | Full-bodied bullish | Flat / fading | 0.121% / 0.066% / -0.060% | Weak move without breakout | 82.1% | 15.8% | 2.1% | 2.33x | 0.211% / 0.265% |
| 2025-06-05 10:00 | 3.25x | Bullish pin-bar / lower rejection | Flat / fading | 0.036% / -0.030% / -0.223% | Weak move without breakout | 43.5% | 11.3% | 45.2% | 1.34x | 0.338% / 0.097% |
| 2025-06-05 23:15 | 2.57x | Bullish pin-bar / lower rejection | Reversal | 0.097% / 0.213% / 0.601% | Liquidity sweep / reversal | 36.2% | 15.5% | 48.3% | 3.02x | 0.049% / 0.601% |
| 2025-06-06 07:00 | 4.87x | Full-bodied bullish | Impulse / continuation | -0.145% / 0.127% / 0.121% | True breakout | 81.6% | 0.0% | 18.4% | 2.38x | 0.217% / 0.157% |
| 2025-06-06 07:30 | 4.24x | Full-bodied bullish | Flat / fading | -0.036% / -0.006% / -0.036% | Position building in range | 61.7% | 25.0% | 13.3% | 2.59x | 0.090% / 0.175% |
| 2025-06-06 10:00 | 2.73x | Bullish pin-bar / lower rejection | Reversal | 0.641% / 1.197% / 0.997% | Liquidity sweep / reversal | 6.0% | 18.0% | 76.0% | 1.82x | 0.000% / 1.324% |
| 2025-06-06 10:15 | 10.34x | Full-bodied bullish | Impulse / continuation | 0.553% / 0.390% / 0.709% | True breakout | 88.3% | 11.7% | 0.0% | 4.11x | 0.745% / 0.144% |
| 2025-06-06 10:30 | 6.82x | Full-bodied bullish | Flat / fading | -0.161% / -0.197% / -0.036% | Weak move without breakout | 67.2% | 15.3% | 17.5% | 3.73x | 0.299% / 0.334% |
| 2025-06-06 10:45 | 5.74x | Small-body bearish | Reversal | -0.036% / 0.317% / 0.353% | Liquidity sweep / reversal | 41.7% | 31.7% | 26.7% | 1.40x | 0.173% / 0.461% |
| 2025-06-06 11:15 | 3.01x | Full-bodied bullish | Flat / fading | -0.191% / 0.036% / -0.036% | Weak move without breakout | 68.2% | 6.8% | 25.0% | 2.05x | 0.143% / 0.262% |
| 2025-06-06 13:15 | 4.70x | Full-bodied bearish | Reversal | 2.697% / 2.514% / 1.946% | Liquidity sweep / reversal | 64.7% | 2.3% | 33.1% | 10.90x | 0.384% / 5.247% |
| 2025-06-06 13:30 | 11.36x | Bearish pin-bar / upper rejection | Flat / fading | -0.178% / -1.337% / -0.689% | Position building in range | 46.5% | 45.3% | 8.2% | 8.60x | 0.404% / 1.889% |
| 2025-06-08 10:00 | 9.94x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.099% / -0.099% / -0.186% | True breakout | 3.7% | 51.9% | 44.4% | 6.20x | 0.211% / 0.000% |
| 2025-06-08 11:15 | 3.79x | Bearish pin-bar / upper rejection | Flat / fading | 0.031% / 0.043% / 0.025% | Position building in range | 11.1% | 44.4% | 44.4% | 2.04x | 0.068% / 0.006% |
| 2025-06-08 13:30 | 3.69x | Bullish pin-bar / lower rejection | Flat / fading | -0.056% / -0.074% / -0.062% | Weak move without breakout | 23.1% | 15.4% | 61.5% | 0.85x | 0.093% / 0.000% |
| 2025-06-08 15:30 | 5.52x | Full-bodied bearish | Impulse / continuation | -0.112% / -0.050% / 0.056% | True breakout | 93.7% | 0.0% | 6.3% | 3.47x | 0.193% / 0.106% |
| 2025-06-08 15:45 | 5.33x | Small-body bearish | Reversal | 0.062% / 0.112% / 0.025% | Liquidity sweep / reversal | 42.9% | 26.2% | 31.0% | 3.77x | 0.000% / 0.218% |
| 2025-06-08 17:00 | 2.76x | Bullish pin-bar / lower rejection | Reversal | 0.050% / -0.031% / 0.137% | Liquidity sweep / reversal | 19.4% | 25.8% | 54.8% | 1.86x | 0.068% / 0.168% |
| 2025-06-09 07:00 | 14.18x | Full-bodied bearish | Flat / fading | 0.305% / 0.262% / 0.118% | Position building in range | 65.5% | 2.0% | 32.4% | 5.41x | 0.044% / 0.511% |
| 2025-06-09 07:15 | 4.17x | Small-body bullish | Flat / fading | -0.044% / 0.037% / -0.068% | Weak move without breakout | 58.3% | 39.3% | 2.4% | 2.40x | 0.131% / 0.348% |
| 2025-06-09 09:00 | 3.23x | Small-body bearish | Reversal | -0.193% / -0.019% / 0.168% | Liquidity sweep / reversal | 38.5% | 32.3% | 29.2% | 1.35x | 0.331% / 0.231% |
| 2025-06-09 09:15 | 3.49x | Bullish pin-bar / lower rejection | Reversal | 0.175% / 0.069% / 0.213% | Liquidity sweep / reversal | 58.5% | 0.0% | 41.5% | 1.04x | 0.069% / 0.425% |
| 2025-06-09 10:00 | 4.20x | Full-bodied bullish | Reversal | -0.149% / -0.673% / -1.165% | Liquidity sweep / reversal | 62.0% | 12.7% | 25.3% | 1.41x | -0.037% / 1.208% |
| 2025-06-09 10:30 | 3.68x | Full-bodied bearish | Impulse / continuation | -0.351% / -0.495% / -0.270% | True breakout | 76.1% | 0.0% | 23.9% | 1.88x | 0.690% / 0.056% |
| 2025-06-09 10:45 | 4.20x | Small-body bearish | Flat / fading | -0.145% / -0.113% / -0.120% | Weak move without breakout | 58.9% | 9.5% | 31.6% | 1.72x | 0.340% / 0.233% |
| 2025-06-09 11:00 | 2.41x | Bearish pin-bar / upper rejection | Reversal | 0.032% / 0.227% / -0.170% | Liquidity sweep / reversal | 53.1% | 43.8% | 3.1% | 0.57x | 0.296% / 0.378% |
| 2025-06-09 11:15 | 2.97x | Bullish pin-bar / lower rejection | Reversal | 0.195% / -0.006% / -0.176% | Liquidity sweep / reversal | 8.0% | 28.0% | 64.0% | 0.92x | 0.346% / 0.328% |
| 2025-06-10 07:00 | 3.28x | Full-bodied bullish | Impulse / continuation | 0.125% / 0.069% / 0.118% | True breakout | 82.5% | 17.5% | 0.0% | 2.53x | 0.311% / 0.012% |
| 2025-06-10 07:15 | 2.77x | Bearish pin-bar / upper rejection | Flat / fading | -0.056% / 0.044% / -0.056% | Weak move without breakout | 38.0% | 60.0% | 2.0% | 2.82x | 0.068% / 0.137% |
| 2025-06-10 09:00 | 3.54x | Bullish pin-bar / lower rejection | Flat / fading | 0.006% / -0.037% / -0.100% | Weak move without breakout | 52.9% | 0.0% | 47.1% | 1.64x | 0.224% / 0.206% |
| 2025-06-10 10:00 | 6.27x | Small-body bearish | Impulse / continuation | -0.225% / -0.281% / -0.237% | True breakout | 33.3% | 37.7% | 29.0% | 2.78x | 0.449% / 0.025% |
| 2025-06-10 10:15 | 3.35x | Full-bodied bearish | Impulse / continuation | -0.056% / -0.044% / -0.069% | True breakout | 84.1% | 6.8% | 9.1% | 1.55x | 0.225% / 0.150% |
| 2025-06-10 10:30 | 2.61x | Small-body bearish | Flat / fading | 0.013% / 0.044% / -0.025% | Weak move without breakout | 38.6% | 36.4% | 25.0% | 1.45x | 0.169% / 0.200% |
| 2025-06-10 10:45 | 2.91x | Bullish pin-bar / lower rejection | Reversal | 0.031% / -0.025% / 0.131% | Liquidity sweep / reversal | 4.4% | 35.6% | 60.0% | 1.47x | 0.213% / 0.169% |
| 2025-06-10 13:00 | 2.72x | Full-bodied bearish | Impulse / continuation | -0.201% / -0.163% / -0.031% | True breakout | 94.9% | 3.4% | 1.7% | 1.44x | 0.364% / 0.151% |
| 2025-06-10 15:00 | 2.33x | Small-body bearish | Impulse / continuation | 0.070% / -0.108% / -0.507% | True breakout | 48.5% | 12.7% | 38.8% | 2.99x | 0.678% / 0.228% |
| 2025-06-11 07:00 | 3.24x | Small-body bullish | Reversal | -0.013% / -0.057% / -0.563% | Liquidity sweep / reversal | 47.4% | 26.3% | 26.3% | 2.31x | 0.051% / 0.576% |
| 2025-06-11 08:15 | 2.72x | Full-bodied bearish | Reversal | 0.300% / 0.293% / 0.345% | Liquidity sweep / reversal | 90.9% | 2.3% | 6.8% | 1.87x | 0.013% / 0.376% |
| 2025-06-11 09:45 | 4.17x | Full-bodied bullish | Impulse / continuation | 0.316% / 0.342% / 0.468% | True breakout | 78.6% | 7.1% | 14.3% | 2.23x | 0.759% / 0.190% |
| 2025-06-11 10:00 | 7.46x | Small-body bullish | Impulse / continuation | 0.025% / 0.095% / 0.296% | True breakout | 53.0% | 20.0% | 27.0% | 2.79x | 0.442% / 0.246% |
| 2025-06-11 10:30 | 3.40x | Bearish pin-bar / upper rejection | Flat / fading | 0.057% / 0.202% / 0.120% | Weak move without breakout | 18.2% | 43.9% | 37.9% | 1.53x | 0.347% / 0.120% |
| 2025-06-13 07:00 | 4.25x | Bearish pin-bar / upper rejection | Reversal | -0.063% / -0.094% / -0.031% | Liquidity sweep / reversal | 10.5% | 81.1% | 8.4% | 3.24x | 0.094% / 0.220% |
| 2025-06-13 09:00 | 3.08x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.391% / -0.668% / -0.536% | True breakout | 51.9% | 3.8% | 44.2% | 1.65x | 0.687% / 0.000% |
| 2025-06-13 09:15 | 3.97x | Full-bodied bearish | Flat / fading | -0.278% / -0.019% / -0.057% | Weak move without breakout | 69.7% | 0.0% | 30.3% | 2.61x | 0.297% / 0.127% |
| 2025-06-13 10:00 | 2.57x | Bullish pin-bar / lower rejection | Reversal | 0.089% / 0.215% / -0.025% | Liquidity sweep / reversal | 46.7% | 0.0% | 53.3% | 0.99x | 0.057% / 0.273% |
| 2025-06-13 12:45 | 2.54x | Full-bodied bullish | Flat / fading | -0.063% / -0.069% / -0.189% | Weak move without breakout | 79.5% | 11.4% | 9.1% | 1.04x | 0.025% / 0.253% |
| 2025-06-13 18:15 | 3.18x | Full-bodied bearish | Impulse / continuation | 0.038% / 0.038% / -0.273% | True breakout | 69.4% | 30.6% | 0.0% | 2.39x | 0.368% / 0.095% |
| 2025-06-13 19:15 | 4.40x | Small-body bearish | Reversal | 0.121% / 0.064% / -0.013% | Liquidity sweep / reversal | 48.9% | 17.8% | 33.3% | 2.72x | 0.032% / 0.153% |
| 2025-06-15 10:00 | 7.03x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.267% / -0.420% / -0.248% | True breakout | 24.5% | 18.9% | 56.6% | 4.36x | 0.458% / -0.038% |
| 2025-06-15 10:15 | 10.09x | Bullish pin-bar / lower rejection | Flat / fading | -0.153% / -0.013% / 0.045% | Position building in range | 53.0% | 1.5% | 45.5% | 4.57x | 0.191% / 0.147% |
| 2025-06-15 10:30 | 8.27x | Full-bodied bearish | Reversal | 0.140% / 0.172% / 0.109% | Liquidity sweep / reversal | 70.0% | 10.0% | 20.0% | 1.56x | 0.038% / 0.300% |
| 2025-06-15 10:45 | 2.66x | Bearish pin-bar / upper rejection | Flat / fading | 0.032% / 0.057% / 0.006% | Position building in range | 35.8% | 47.2% | 17.0% | 2.52x | 0.102% / 0.134% |
| 2025-06-16 07:00 | 13.44x | Small-body bullish | Flat / fading | -0.013% / -0.064% / -0.038% | Position building in range | 37.5% | 37.5% | 25.0% | 7.34x | 0.038% / 0.121% |
| 2025-06-16 10:00 | 15.26x | Bearish pin-bar / upper rejection | Reversal | 0.032% / -0.140% / -0.559% | Liquidity sweep / reversal | 27.1% | 56.5% | 16.5% | 4.28x | 0.076% / 0.940% |
| 2025-06-16 10:30 | 3.10x | Small-body bearish | Impulse / continuation | -0.388% / -0.420% / -0.280% | True breakout | 49.1% | 13.2% | 37.7% | 2.02x | 0.802% / 0.038% |
| 2025-06-16 10:45 | 8.82x | Bullish pin-bar / lower rejection | Flat / fading | -0.032% / 0.032% / 0.198% | Position building in range | 46.2% | 4.5% | 49.2% | 5.18x | 0.345% / 0.300% |
| 2025-06-16 12:45 | 2.84x | Full-bodied bullish | Impulse / continuation | 0.324% / 0.216% / 0.114% | True breakout | 71.2% | 18.2% | 10.6% | 1.49x | 0.457% / -0.013% |
| 2025-06-16 14:15 | 2.53x | Small-body bullish | Flat / fading | -0.063% / -0.095% / 0.171% | Weak move without breakout | 54.1% | 21.6% | 24.3% | 0.80x | 0.253% / 0.215% |
| 2025-06-16 22:00 | 2.63x | Full-bodied bearish | Flat / fading | 0.013% / 0.019% / 0.064% | Position building in range | 72.7% | 0.0% | 27.3% | 1.36x | 0.006% / 0.095% |
| 2025-06-17 07:00 | 3.31x | Bearish pin-bar / upper rejection | Reversal | -0.032% / -0.108% / 0.127% | Liquidity sweep / reversal | 27.5% | 70.0% | 2.5% | 2.86x | 0.171% / 0.165% |
| 2025-06-17 07:45 | 2.55x | Bearish pin-bar / upper rejection | Flat / fading | 0.101% / 0.082% / 0.114% | Weak move without breakout | 45.7% | 47.8% | 6.5% | 2.76x | 0.234% / 0.000% |
| 2025-06-17 10:00 | 8.17x | Full-bodied bullish | Impulse / continuation | 0.241% / 0.247% / 0.506% | True breakout | 71.4% | 0.0% | 28.6% | 2.09x | 0.652% / 0.006% |
| 2025-06-17 10:15 | 6.63x | Full-bodied bullish | Impulse / continuation | 0.006% / 0.240% / 0.316% | True breakout | 74.5% | 23.5% | 2.0% | 2.26x | 0.436% / 0.088% |
| 2025-06-17 10:30 | 3.81x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.234% / 0.259% / 0.455% | True breakout | 3.0% | 54.5% | 42.4% | 1.27x | 0.524% / 0.038% |
| 2025-06-17 10:45 | 4.51x | Full-bodied bullish | Impulse / continuation | 0.025% / 0.076% / 0.315% | True breakout | 64.9% | 24.6% | 10.5% | 2.24x | 0.378% / 0.032% |
| 2025-06-17 11:00 | 2.98x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.050% / 0.195% / 0.208% | True breakout | 3.1% | 71.9% | 25.0% | 1.13x | 0.378% / 0.000% |
| 2025-06-17 12:00 | 2.40x | Bearish pin-bar / upper rejection | Reversal | 0.101% / 0.138% / 0.132% | Liquidity sweep / reversal | 38.7% | 48.4% | 12.9% | 1.05x | 0.025% / 0.327% |
| 2025-06-17 17:45 | 5.15x | Full-bodied bullish | Flat / fading | 0.031% / 0.224% / 0.125% | Weak move without breakout | 81.3% | 17.7% | 1.0% | 3.34x | 0.243% / 0.025% |
| 2025-06-17 18:00 | 3.32x | Bearish pin-bar / upper rejection | Flat / fading | 0.193% / 0.056% / 0.050% | Position building in range | 11.6% | 79.1% | 9.3% | 1.28x | 0.193% / 0.056% |
| 2025-06-18 07:00 | 4.74x | Bullish pin-bar / lower rejection | Reversal | -0.205% / -0.242% / -0.043% | Liquidity sweep / reversal | 32.8% | 26.6% | 40.6% | 2.32x | 0.000% / 0.273% |
| 2025-06-18 10:00 | 3.69x | Small-body bearish | Impulse / continuation | -0.236% / -0.230% / -0.193% | True breakout | 46.2% | 35.9% | 17.9% | 1.39x | 0.416% / 0.012% |
| 2025-06-18 10:15 | 3.80x | Full-bodied bearish | Flat / fading | 0.006% / -0.025% / 0.081% | Weak move without breakout | 61.5% | 0.0% | 38.5% | 2.15x | 0.181% / 0.168% |
| 2025-06-18 16:15 | 6.43x | Full-bodied bearish | Flat / fading | 0.295% / 0.282% / 0.100% | Position building in range | 71.1% | 3.9% | 25.0% | 5.65x | 0.138% / 0.420% |
| 2025-06-19 07:00 | 5.75x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / 0.000% / -0.056% | Weak move without breakout | 50.0% | 50.0% | 0.0% | 4.36x | 0.119% / 0.187% |
| 2025-06-19 10:00 | 3.19x | Small-body bullish | Impulse / continuation | 0.175% / 0.437% / 0.450% | True breakout | 29.2% | 33.3% | 37.5% | 1.22x | 0.537% / 0.019% |
| 2025-06-19 10:30 | 6.68x | Full-bodied bullish | Flat / fading | -0.087% / 0.012% / -0.100% | Weak move without breakout | 77.8% | 7.4% | 14.8% | 2.42x | 0.100% / 0.162% |
| 2025-06-19 10:45 | 3.02x | Small-body bearish | Reversal | 0.100% / -0.006% / -0.044% | Liquidity sweep / reversal | 36.4% | 33.3% | 30.3% | 1.47x | 0.193% / 0.187% |
| 2025-06-19 15:00 | 3.03x | Full-bodied bearish | Flat / fading | 0.013% / -0.006% / 0.019% | Weak move without breakout | 85.7% | 0.0% | 14.3% | 2.65x | 0.107% / 0.157% |
| 2025-06-19 15:15 | 3.29x | Bearish pin-bar / upper rejection | Reversal | -0.019% / -0.006% / -0.088% | Liquidity sweep / reversal | 5.3% | 50.0% | 44.7% | 1.45x | 0.144% / 0.169% |
| 2025-06-19 16:30 | 2.34x | Bullish pin-bar / lower rejection | Flat / fading | 0.019% / 0.000% / 0.151% | Position building in range | 49.2% | 1.7% | 49.2% | 2.04x | 0.138% / 0.151% |
| 2025-06-20 07:00 | 5.99x | Small-body bullish | Flat / fading | 0.088% / 0.044% / 0.025% | Position building in range | 24.1% | 38.0% | 38.0% | 5.91x | 0.132% / 0.019% |
| 2025-06-20 10:00 | 2.61x | Small-body bearish | Reversal | -0.088% / -0.031% / 0.163% | Liquidity sweep / reversal | 53.3% | 13.3% | 33.3% | 1.41x | 0.195% / 0.270% |
| 2025-06-20 10:15 | 5.52x | Bullish pin-bar / lower rejection | Reversal | 0.057% / 0.245% / 0.239% | Liquidity sweep / reversal | 34.1% | 24.4% | 41.5% | 1.79x | 0.038% / 0.358% |
| 2025-06-20 10:30 | 2.87x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.188% / 0.195% / 0.176% | True breakout | 27.3% | 54.5% | 18.2% | 1.32x | 0.302% / 0.000% |
| 2025-06-20 13:45 | 2.63x | Full-bodied bullish | Flat / fading | 0.063% / 0.006% / -0.144% | Weak move without breakout | 60.5% | 25.6% | 14.0% | 2.16x | 0.094% / 0.225% |
| 2025-06-20 16:00 | 3.33x | Full-bodied bearish | Impulse / continuation | -0.132% / -0.176% / -0.176% | True breakout | 60.9% | 14.1% | 25.0% | 3.04x | 0.339% / 0.113% |
| 2025-06-20 16:15 | 3.08x | Small-body bearish | Flat / fading | -0.044% / -0.094% / 0.000% | Weak move without breakout | 35.6% | 30.5% | 33.9% | 2.42x | 0.208% / 0.050% |
| 2025-06-20 16:30 | 2.60x | Bullish pin-bar / lower rejection | Flat / fading | -0.050% / 0.000% / -0.019% | Weak move without breakout | 17.1% | 19.5% | 63.4% | 1.51x | 0.157% / 0.120% |
| 2025-06-23 09:15 | 4.27x | Small-body bearish | Impulse / continuation | 0.051% / 0.051% / -0.484% | True breakout | 59.4% | 15.6% | 25.0% | 3.02x | 0.580% / 0.153% |
| 2025-06-23 10:00 | 4.79x | Small-body bearish | Impulse / continuation | -0.325% / -0.408% / -0.179% | True breakout | 55.6% | 22.2% | 22.2% | 2.52x | 0.440% / 0.006% |
| 2025-06-23 10:15 | 5.18x | Full-bodied bearish | Flat / fading | -0.083% / 0.141% / 0.192% | Weak move without breakout | 77.6% | 0.0% | 22.4% | 2.41x | 0.115% / 0.243% |
| 2025-06-23 16:30 | 5.94x | Full-bodied bullish | Impulse / continuation | 0.057% / 0.403% / 0.252% | True breakout | 71.7% | 27.6% | 0.8% | 4.93x | 0.517% / 0.038% |
| 2025-06-23 17:00 | 2.85x | Full-bodied bullish | Flat / fading | -0.063% / -0.151% / -0.094% | Position building in range | 74.3% | 25.7% | 0.0% | 2.18x | 0.050% / 0.301% |
| 2025-06-24 07:00 | 3.51x | Small-body bullish | Impulse / continuation | 0.189% / 0.164% / 0.447% | True breakout | 57.8% | 19.3% | 22.9% | 4.05x | 0.504% / 0.025% |
| 2025-06-24 08:00 | 2.63x | Full-bodied bullish | Reversal | -0.082% / -0.201% / -0.533% | Liquidity sweep / reversal | 64.4% | 15.3% | 20.3% | 2.26x | 0.044% / 0.684% |
| 2025-06-24 09:00 | 4.51x | Small-body bearish | Impulse / continuation | -0.151% / -0.120% / -0.460% | True breakout | 41.8% | 27.8% | 30.4% | 2.47x | 0.479% / 0.069% |
| 2025-06-24 09:45 | 4.15x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.221% / -0.209% / -0.044% | True breakout | 38.8% | 0.0% | 61.2% | 1.24x | 0.493% / 0.196% |
| 2025-06-24 10:00 | 3.33x | Bearish pin-bar / upper rejection | Reversal | 0.013% / 0.013% / 0.266% | Liquidity sweep / reversal | 46.4% | 49.3% | 4.3% | 1.69x | 0.272% / 0.425% |
| 2025-06-24 10:15 | 4.63x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.000% / 0.165% / -0.266% | False breakout | 3.8% | 15.1% | 81.1% | 1.21x | 0.412% / 0.367% |
| 2025-06-24 11:15 | 3.10x | Full-bodied bearish | Flat / fading | 0.152% / 0.280% / 0.178% | Position building in range | 81.2% | 3.0% | 15.8% | 2.33x | 0.057% / 0.451% |
| 2025-06-24 17:15 | 2.81x | Bearish pin-bar / upper rejection | Flat / fading | 0.114% / 0.221% / 0.240% | Weak move without breakout | 14.3% | 85.7% | 0.0% | 0.88x | 0.315% / 0.057% |
| 2025-06-24 21:15 | 3.01x | Full-bodied bullish | Flat / fading | -0.063% / 0.006% / 0.220% | Weak move without breakout | 64.3% | 35.7% | 0.0% | 2.44x | 0.220% / 0.075% |
| 2025-06-25 07:00 | 3.42x | Small-body bearish | Flat / fading | -0.157% / 0.013% / -0.081% | Weak move without breakout | 30.0% | 30.0% | 40.0% | 1.34x | 0.207% / 0.063% |
| 2025-06-25 10:00 | 3.65x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.238% / 0.425% / 0.650% | True breakout | 17.8% | 26.7% | 55.6% | 1.53x | 0.694% / 0.019% |
| 2025-06-25 10:15 | 3.51x | Full-bodied bullish | Impulse / continuation | 0.187% / 0.162% / 0.530% | True breakout | 66.1% | 33.9% | 0.0% | 2.13x | 0.698% / 0.000% |
| 2025-06-25 10:30 | 2.89x | Full-bodied bullish | Impulse / continuation | -0.025% / 0.224% / 0.268% | True breakout | 88.2% | 11.8% | 0.0% | 1.04x | 0.510% / 0.131% |
| 2025-06-25 11:00 | 4.24x | Full-bodied bullish | Impulse / continuation | 0.118% / 0.043% / -0.143% | True breakout | 78.4% | 13.7% | 7.8% | 1.63x | 0.286% / 0.143% |
| 2025-06-25 11:15 | 3.44x | Bearish pin-bar / upper rejection | Reversal | -0.074% / -0.037% / -0.087% | Liquidity sweep / reversal | 35.8% | 50.9% | 13.2% | 1.63x | 0.056% / 0.304% |
| 2025-06-25 17:00 | 3.28x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.223% / 0.167% / 0.118% | True breakout | 14.5% | 5.3% | 80.3% | 2.60x | 0.297% / 0.000% |
| 2025-06-26 07:00 | 8.08x | Full-bodied bullish | Flat / fading | -0.098% / -0.067% / -0.147% | Weak move without breakout | 75.3% | 6.5% | 18.3% | 6.26x | 0.080% / 0.166% |
| 2025-06-26 10:00 | 5.32x | Small-body bearish | Impulse / continuation | -0.043% / -0.135% / -0.135% | True breakout | 58.0% | 10.0% | 32.0% | 1.90x | 0.283% / 0.031% |
| 2025-06-26 20:00 | 5.20x | Bullish pin-bar / lower rejection | Flat / fading | 0.074% / 0.074% / -0.087% | Position building in range | 45.7% | 0.0% | 54.3% | 4.18x | 0.099% / 0.173% |
| 2025-06-27 07:00 | 3.20x | Small-body bearish | Flat / fading | -0.049% / 0.025% / -0.031% | Weak move without breakout | 52.6% | 7.9% | 39.5% | 2.24x | 0.099% / 0.043% |
| 2025-06-27 10:00 | 4.57x | Full-bodied bearish | Flat / fading | 0.068% / 0.105% / 0.105% | Weak move without breakout | 61.0% | 17.1% | 22.0% | 2.22x | 0.118% / 0.149% |
| 2025-06-27 10:30 | 4.50x | Bullish pin-bar / lower rejection | Reversal | -0.093% / 0.000% / 0.025% | Liquidity sweep / reversal | 17.5% | 10.0% | 72.5% | 2.06x | 0.099% / 0.161% |
| 2025-06-27 16:15 | 2.83x | Full-bodied bullish | Impulse / continuation | 0.080% / 0.222% / 0.327% | True breakout | 76.5% | 2.9% | 20.6% | 2.11x | 0.345% / 0.056% |
| 2025-06-27 16:30 | 3.32x | Small-body bullish | Impulse / continuation | 0.142% / 0.136% / 0.080% | True breakout | 53.6% | 21.4% | 25.0% | 1.59x | 0.265% / 0.136% |
| 2025-06-27 16:45 | 2.80x | Small-body bullish | Flat / fading | -0.006% / 0.105% / 0.000% | Weak move without breakout | 53.1% | 8.2% | 38.8% | 2.68x | 0.123% / 0.111% |
| 2025-06-27 17:00 | 2.31x | Bearish pin-bar / upper rejection | Reversal | 0.111% / -0.055% / 0.191% | Liquidity sweep / reversal | 5.7% | 54.3% | 40.0% | 1.70x | 0.105% / 0.215% |
| 2025-06-27 17:30 | 2.39x | Full-bodied bearish | Reversal | 0.062% / 0.246% / 0.191% | Liquidity sweep / reversal | 71.1% | 7.9% | 21.1% | 1.66x | 0.012% / 0.302% |
| 2025-06-27 18:00 | 2.16x | Full-bodied bullish | Flat / fading | 0.012% / -0.055% / -0.074% | Weak move without breakout | 87.1% | 12.9% | 0.0% | 1.28x | 0.055% / 0.092% |
| 2025-06-28 10:00 | 3.23x | Small-body bullish | Flat / fading | 0.104% / 0.055% / 0.031% | Position building in range | 59.4% | 36.6% | 4.0% | 12.74x | 0.128% / 0.104% |
| 2025-06-29 13:15 | 2.57x | Bullish pin-bar / lower rejection | Flat / fading | 0.012% / 0.000% / 0.006% | Weak move without breakout | 33.3% | 0.0% | 66.7% | 1.04x | 0.018% / 0.024% |
| 2025-06-29 15:45 | 5.14x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.024% / 0.073% / 0.067% | True breakout | 60.0% | 40.0% | 0.0% | 1.30x | 0.318% / 0.012% |
| 2025-06-29 16:15 | 32.42x | Bearish pin-bar / upper rejection | Reversal | 0.079% / -0.006% / -0.092% | Liquidity sweep / reversal | 16.3% | 81.6% | 2.0% | 12.25x | 0.171% / 0.128% |
| 2025-06-29 16:30 | 6.59x | Bearish pin-bar / upper rejection | Reversal | -0.085% / -0.165% / -0.153% | Liquidity sweep / reversal | 10.7% | 53.6% | 35.7% | 3.96x | 0.000% / 0.208% |
| 2025-06-29 16:45 | 4.37x | Small-body bearish | Impulse / continuation | -0.079% / -0.086% / -0.055% | True breakout | 52.4% | 14.3% | 33.3% | 2.39x | 0.122% / 0.024% |
| 2025-06-30 09:45 | 2.96x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.079% / -0.073% / -0.469% | False breakout | 13.0% | 30.4% | 56.5% | 1.59x | 0.171% / 0.603% |
| 2025-06-30 10:00 | 11.10x | Bearish pin-bar / upper rejection | Reversal | -0.152% / -0.530% / -0.579% | Liquidity sweep / reversal | 46.9% | 46.9% | 6.3% | 2.06x | 0.061% / 0.682% |
| 2025-06-30 10:15 | 4.02x | Full-bodied bearish | Impulse / continuation | -0.378% / -0.396% / -0.750% | True breakout | 67.6% | 27.0% | 5.4% | 2.12x | 0.781% / 0.030% |
| 2025-06-30 10:30 | 8.28x | Full-bodied bearish | Impulse / continuation | -0.018% / -0.049% / -0.257% | True breakout | 78.2% | 7.7% | 14.1% | 3.91x | 0.471% / 0.135% |
| 2025-06-30 10:45 | 3.90x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.031% / -0.355% / -0.343% | True breakout | 8.9% | 42.2% | 48.9% | 1.89x | 0.453% / 0.153% |
| 2025-06-30 11:00 | 2.62x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.325% / -0.208% / -0.214% | True breakout | 3.0% | 87.9% | 9.1% | 1.27x | 0.423% / 0.043% |
| 2025-06-30 11:15 | 4.14x | Full-bodied bearish | Flat / fading | 0.117% / 0.012% / 0.172% | Weak move without breakout | 80.0% | 12.3% | 7.7% | 2.37x | 0.098% / 0.246% |
| 2025-06-30 13:00 | 2.63x | Full-bodied bullish | Impulse / continuation | 0.092% / 0.251% / 0.165% | True breakout | 82.8% | 6.9% | 10.3% | 2.23x | 0.288% / 0.092% |
| 2025-07-01 07:00 | 5.22x | Doji | Impulse / continuation | 0.049% / 0.153% / 0.135% | True breakout | 0.0% | 41.0% | 59.0% | 6.58x | 0.153% / 0.153% |
| 2025-07-01 07:30 | 3.70x | Full-bodied bullish | Reversal | -0.031% / -0.018% / -0.079% | Liquidity sweep / reversal | 100.0% | 0.0% | 0.0% | 1.82x | 0.000% / 0.159% |
| 2025-07-01 09:15 | 2.78x | Full-bodied bullish | Impulse -> reversal | 0.024% / 0.018% / -0.085% | False breakout | 73.8% | 0.0% | 26.2% | 2.71x | 0.098% / 0.317% |
| 2025-07-01 10:00 | 6.56x | Full-bodied bearish | Reversal | 0.110% / 0.061% / 0.330% | Liquidity sweep / reversal | 77.6% | 2.0% | 20.4% | 2.41x | 0.122% / 0.385% |
| 2025-07-01 10:15 | 3.45x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.049% / 0.031% / 0.220% | True breakout | 44.2% | 11.6% | 44.2% | 1.87x | 0.330% / 0.073% |
| 2025-07-01 11:00 | 4.04x | Full-bodied bullish | Reversal | 0.000% / -0.079% / -0.238% | Liquidity sweep / reversal | 77.5% | 22.5% | 0.0% | 1.65x | 0.110% / 0.384% |
| 2025-07-01 11:15 | 3.71x | Doji | Impulse / continuation | -0.079% / -0.146% / -0.152% | True breakout | 0.0% | 60.0% | 40.0% | 1.16x | 0.384% / 0.384% |
| 2025-07-01 12:00 | 2.69x | Bullish pin-bar / lower rejection | Reversal | 0.085% / 0.067% / 0.061% | Liquidity sweep / reversal | 34.1% | 7.3% | 58.5% | 1.46x | 0.061% / 0.147% |
| 2025-07-01 14:45 | 2.23x | Full-bodied bullish | Impulse / continuation | 0.122% / 0.201% / 0.164% | True breakout | 73.7% | 21.1% | 5.3% | 1.81x | 0.231% / 0.036% |
| 2025-07-01 16:45 | 2.62x | Full-bodied bearish | Flat / fading | 0.030% / 0.061% / -0.024% | Weak move without breakout | 62.5% | 32.5% | 5.0% | 1.94x | 0.091% / 0.128% |
| 2025-07-02 09:15 | 2.80x | Full-bodied bearish | Impulse / continuation | -0.012% / 0.012% / -0.024% | True breakout | 93.5% | 6.5% | 0.0% | 2.08x | 0.361% / 0.049% |
| 2025-07-02 09:30 | 7.80x | Bullish pin-bar / lower rejection | Reversal | 0.024% / -0.177% / -0.031% | Liquidity sweep / reversal | 3.1% | 9.2% | 87.7% | 4.04x | 0.269% / 0.061% |
| 2025-07-02 10:00 | 2.92x | Full-bodied bearish | Flat / fading | 0.165% / 0.147% / 0.061% | Position building in range | 69.4% | 0.0% | 30.6% | 2.41x | 0.073% / 0.208% |
| 2025-07-02 10:15 | 2.62x | Full-bodied bullish | Flat / fading | -0.018% / -0.128% / -0.073% | Weak move without breakout | 64.3% | 7.1% | 28.6% | 1.83x | 0.043% / 0.373% |
| 2025-07-02 11:15 | 3.95x | Bullish pin-bar / lower rejection | Reversal | 0.037% / -0.184% / -0.147% | Liquidity sweep / reversal | 8.5% | 16.9% | 74.6% | 2.16x | 0.110% / 0.410% |
| 2025-07-02 12:00 | 2.62x | Bullish pin-bar / lower rejection | Reversal | 0.043% / 0.098% / -0.043% | Liquidity sweep / reversal | 4.9% | 7.3% | 87.8% | 1.19x | 0.129% / 0.172% |
| 2025-07-02 18:30 | 2.74x | Full-bodied bearish | Reversal | 0.006% / 0.264% / 0.123% | Liquidity sweep / reversal | 70.5% | 0.0% | 29.5% | 1.63x | -0.006% / 0.368% |
| 2025-07-02 19:00 | 2.62x | Small-body bullish | Reversal | -0.116% / -0.141% / 0.000% | Liquidity sweep / reversal | 48.9% | 37.8% | 13.3% | 1.64x | 0.073% / 0.159% |
| 2025-07-03 09:45 | 5.23x | Bullish pin-bar / lower rejection | Flat / fading | -0.025% / -0.092% / 0.049% | Weak move without breakout | 52.6% | 2.6% | 44.7% | 3.11x | 0.165% / 0.092% |
| 2025-07-03 10:00 | 7.26x | Bullish pin-bar / lower rejection | Reversal | -0.067% / -0.049% / 0.337% | Liquidity sweep / reversal | 12.9% | 19.4% | 67.7% | 2.18x | 0.141% / 0.410% |
| 2025-07-03 10:15 | 4.21x | Bearish pin-bar / upper rejection | Reversal | 0.018% / 0.141% / 0.362% | Liquidity sweep / reversal | 41.7% | 45.8% | 12.5% | 1.65x | 0.074% / 0.478% |
| 2025-07-03 10:30 | 4.32x | Doji | Impulse / continuation | 0.123% / 0.386% / 0.337% | True breakout | 0.0% | 50.0% | 50.0% | 1.95x | 0.460% / 0.460% |
| 2025-07-03 10:45 | 5.13x | Small-body bullish | Impulse / continuation | 0.263% / 0.220% / 0.300% | True breakout | 54.3% | 20.0% | 25.7% | 2.23x | 0.337% / 0.031% |
| 2025-07-03 11:00 | 5.99x | Full-bodied bullish | Flat / fading | -0.043% / -0.049% / 0.018% | Weak move without breakout | 63.3% | 20.0% | 16.7% | 3.44x | 0.110% / 0.085% |
| 2025-07-03 11:15 | 3.83x | Bearish pin-bar / upper rejection | Reversal | -0.006% / 0.079% / 0.073% | Liquidity sweep / reversal | 28.0% | 44.0% | 28.0% | 1.17x | 0.043% / 0.153% |
| 2025-07-03 16:15 | 3.53x | Bearish pin-bar / upper rejection | Flat / fading | 0.122% / 0.098% / 0.122% | Weak move without breakout | 50.0% | 48.2% | 1.8% | 2.18x | 0.190% / 0.018% |
| 2025-07-04 07:00 | 4.14x | Bullish pin-bar / lower rejection | Reversal | 0.006% / 0.154% / 0.012% | Liquidity sweep / reversal | 5.6% | 12.5% | 81.9% | 2.90x | 0.235% / 0.216% |
| 2025-07-04 09:00 | 4.82x | Bearish pin-bar / upper rejection | Flat / fading | -0.062% / 0.074% / 0.160% | Position building in range | 44.6% | 55.4% | 0.0% | 3.35x | 0.240% / 0.234% |
| 2025-07-04 10:00 | 3.69x | Small-body bullish | Reversal | 0.068% / -0.049% / -0.658% | Liquidity sweep / reversal | 57.1% | 16.9% | 26.0% | 2.14x | 0.141% / 0.720% |
| 2025-07-04 10:15 | 2.73x | Bullish pin-bar / lower rejection | Reversal | -0.117% / -0.301% / -0.695% | Liquidity sweep / reversal | 31.8% | 27.3% | 40.9% | 1.09x | 0.025% / 0.787% |
| 2025-07-04 11:00 | 4.77x | Full-bodied bearish | Flat / fading | 0.031% / -0.211% / -0.229% | Weak move without breakout | 69.9% | 19.4% | 10.8% | 2.35x | 0.297% / 0.142% |
| 2025-07-04 11:15 | 2.62x | Bearish pin-bar / upper rejection | Reversal | -0.241% / -0.124% / -0.291% | Liquidity sweep / reversal | 15.6% | 56.2% | 28.1% | 0.74x | 0.000% / 0.396% |
| 2025-07-05 18:45 | 3.79x | Full-bodied bullish | Reversal | -0.012% / -0.124% / -0.211% | Liquidity sweep / reversal | 66.7% | 0.0% | 33.3% | 0.82x | -0.012% / 0.398% |
| 2025-07-06 10:00 | 5.76x | Full-bodied bearish | Impulse / continuation | -0.112% / -0.087% / -0.230% | True breakout | 72.0% | 0.0% | 28.0% | 7.45x | 0.318% / 0.019% |
| 2025-07-06 10:15 | 18.49x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.025% / 0.012% / -0.106% | True breakout | 38.3% | 6.4% | 55.3% | 9.68x | 0.206% / 0.031% |
| 2025-07-06 11:00 | 4.90x | Full-bodied bearish | Reversal | 0.012% / 0.125% / 0.162% | Liquidity sweep / reversal | 60.0% | 0.0% | 40.0% | 4.15x | 0.056% / 0.162% |
| 2025-07-06 17:30 | 2.88x | Full-bodied bullish | Impulse / continuation | -0.012% / -0.012% / 0.006% | True breakout | 87.5% | 12.5% | 0.0% | 2.67x | 0.031% / 0.019% |
| 2025-07-07 07:00 | 45.17x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.087% / -0.112% / -0.118% | True breakout | 25.0% | 16.7% | 58.3% | 9.08x | 0.268% / 0.000% |
| 2025-07-07 07:15 | 4.52x | Full-bodied bearish | Impulse / continuation | -0.025% / -0.025% / -0.094% | True breakout | 70.0% | 0.0% | 30.0% | 2.33x | 0.181% / 0.012% |
| 2025-07-07 07:30 | 6.72x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / -0.006% / -0.094% | Weak move without breakout | 13.8% | 0.0% | 86.2% | 2.94x | 0.137% / 0.037% |
| 2025-07-07 07:45 | 2.54x | Doji / lower rejection | Flat / fading | -0.006% / -0.069% / -0.050% | Weak move without breakout | 0.0% | 5.9% | 94.1% | 1.44x | 0.137% / 0.137% |
| 2025-07-07 09:00 | 6.46x | Full-bodied bullish | Impulse / continuation | -0.100% / 0.012% / 0.012% | True breakout | 89.3% | 10.7% | 0.0% | 2.00x | 0.112% / 0.118% |
| 2025-07-07 10:00 | 6.38x | Bearish pin-bar / upper rejection | Reversal | -0.056% / -0.100% / 0.000% | Liquidity sweep / reversal | 32.4% | 43.2% | 24.3% | 1.86x | 0.062% / 0.156% |
| 2025-07-07 10:15 | 4.71x | Bullish pin-bar / lower rejection | Reversal | -0.044% / 0.025% / 0.137% | Liquidity sweep / reversal | 33.3% | 0.0% | 66.7% | 1.08x | 0.087% / 0.137% |
| 2025-07-07 12:30 | 6.55x | Full-bodied bullish | Flat / fading | 0.093% / 0.056% / -0.186% | Weak move without breakout | 70.7% | 22.2% | 7.1% | 4.19x | 0.229% / 0.273% |
| 2025-07-07 12:45 | 4.75x | Bearish pin-bar / upper rejection | Reversal | -0.037% / -0.180% / -0.316% | Liquidity sweep / reversal | 26.4% | 41.5% | 32.1% | 1.86x | 0.081% / 0.409% |
| 2025-07-07 20:45 | 12.53x | Full-bodied bearish | Flat / fading | 0.006% / -0.063% / -0.063% | Position building in range | 72.8% | 1.2% | 25.9% | 5.79x | 0.131% / 0.050% |
| 2025-07-08 07:00 | 3.40x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.025% / -0.163% | Liquidity sweep / reversal | 18.5% | 9.3% | 72.2% | 3.07x | 0.088% / 0.213% |
| 2025-07-08 10:00 | 10.39x | Bearish pin-bar / upper rejection | Reversal | -0.213% / 0.038% / 0.038% | Liquidity sweep / reversal | 8.5% | 68.1% | 23.4% | 2.38x | 0.131% / 0.250% |
| 2025-07-08 10:15 | 6.23x | Small-body bearish | Reversal | 0.251% / 0.289% / 0.257% | Liquidity sweep / reversal | 58.6% | 34.5% | 6.9% | 2.60x | 0.038% / 0.345% |
| 2025-07-08 10:30 | 2.98x | Full-bodied bullish | Flat / fading | 0.038% / 0.000% / 0.088% | Weak move without breakout | 81.6% | 6.1% | 12.2% | 1.88x | 0.169% / 0.156% |
| 2025-07-08 19:15 | 4.49x | Full-bodied bearish | Impulse / continuation | -0.307% / -0.608% / -0.565% | True breakout | 67.1% | 0.0% | 32.9% | 3.44x | 0.828% / 0.019% |
| 2025-07-08 19:30 | 3.11x | Full-bodied bearish | Impulse / continuation | -0.302% / -0.233% / -0.302% | True breakout | 71.0% | 4.3% | 24.6% | 2.47x | 0.522% / 0.000% |
| 2025-07-08 19:45 | 2.53x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.069% / 0.044% / -0.379% | True breakout | 57.8% | 0.0% | 42.2% | 2.69x | 0.530% / 0.126% |
| 2025-07-09 09:45 | 7.84x | Full-bodied bullish | Reversal | -0.221% / -0.265% / -0.302% | Liquidity sweep / reversal | 74.5% | 16.4% | 9.1% | 3.21x | 0.025% / 0.548% |
| 2025-07-09 10:00 | 6.67x | Full-bodied bearish | Impulse / continuation | -0.044% / -0.183% / -0.170% | True breakout | 90.0% | 7.5% | 2.5% | 1.99x | 0.328% / 0.208% |
| 2025-07-09 10:15 | 4.76x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.139% / -0.038% / 0.057% | False breakout | 17.1% | 80.5% | 2.4% | 1.86x | 0.284% / 0.158% |
| 2025-07-09 10:30 | 3.77x | Bullish pin-bar / lower rejection | Reversal | 0.101% / 0.013% / 0.158% | Liquidity sweep / reversal | 48.9% | 0.0% | 51.1% | 1.83x | 0.101% / 0.297% |
| 2025-07-09 12:15 | 3.58x | Full-bodied bearish | Flat / fading | 0.120% / -0.019% / 0.126% | Weak move without breakout | 64.6% | 6.2% | 29.2% | 1.98x | 0.170% / 0.189% |
| 2025-07-10 07:45 | 2.85x | Bearish pin-bar / upper rejection | Reversal | -0.113% / -0.313% / -0.294% | Liquidity sweep / reversal | 55.2% | 41.4% | 3.4% | 1.74x | 0.038% / 0.676% |
| 2025-07-10 08:15 | 5.74x | Bullish pin-bar / lower rejection | Flat / fading | 0.025% / 0.019% / 0.119% | Position building in range | 28.1% | 21.1% | 50.9% | 6.00x | 0.025% / 0.163% |
| 2025-07-10 10:00 | 3.58x | Bullish pin-bar / lower rejection | Reversal | -0.006% / -0.063% / -0.131% | Liquidity sweep / reversal | 41.0% | 2.6% | 56.4% | 1.51x | 0.088% / 0.182% |
| 2025-07-10 14:00 | 3.05x | Bullish pin-bar / lower rejection | Reversal | -0.006% / 0.063% / -0.170% | Liquidity sweep / reversal | 20.9% | 14.0% | 65.1% | 1.77x | 0.107% / 0.220% |
| 2025-07-10 15:45 | 3.12x | Full-bodied bullish | Impulse / continuation | 0.163% / 0.106% / 0.213% | True breakout | 69.5% | 15.3% | 15.3% | 2.00x | 0.294% / 0.031% |
| 2025-07-10 16:00 | 2.63x | Full-bodied bullish | Impulse / continuation | -0.056% / 0.037% / 0.125% | True breakout | 78.1% | 3.1% | 18.8% | 1.02x | 0.237% / 0.125% |
| 2025-07-11 07:00 | 5.64x | Bullish pin-bar / lower rejection | Reversal | -0.081% / -0.150% / -0.300% | Liquidity sweep / reversal | 22.7% | 31.8% | 45.5% | 3.58x | 0.069% / 0.300% |
| 2025-07-11 08:00 | 3.66x | Full-bodied bearish | Impulse / continuation | -0.025% / -0.069% / -0.200% | True breakout | 93.5% | 6.5% | 0.0% | 2.13x | 0.288% / 0.056% |
| 2025-07-11 08:15 | 3.33x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.044% / -0.013% / -0.094% | True breakout | 17.4% | 8.7% | 73.9% | 1.42x | 0.263% / 0.081% |
| 2025-07-11 09:00 | 2.94x | Small-body bearish | Flat / fading | 0.082% / 0.019% / 0.119% | Weak move without breakout | 55.0% | 10.0% | 35.0% | 2.40x | 0.125% / 0.245% |
| 2025-07-11 10:00 | 4.17x | Small-body bullish | Reversal | -0.175% / -0.075% / -0.194% | Liquidity sweep / reversal | 53.7% | 37.0% | 9.3% | 2.44x | 0.038% / 0.251% |
| 2025-07-11 11:30 | 4.18x | Full-bodied bearish | Impulse / continuation | -0.038% / -0.126% / -0.258% | True breakout | 72.7% | 0.0% | 27.3% | 2.00x | 0.366% / 0.019% |
| 2025-07-11 12:15 | 2.69x | Full-bodied bearish | Flat / fading | 0.038% / 0.000% / 0.164% | Weak move without breakout | 78.8% | 3.0% | 18.2% | 1.09x | 0.070% / 0.190% |
| 2025-07-11 17:30 | 4.49x | Full-bodied bearish | Impulse / continuation | -0.063% / -0.076% / -0.348% | True breakout | 94.6% | 1.8% | 3.6% | 2.40x | 0.494% / 0.082% |
| 2025-07-11 18:15 | 5.86x | Small-body bearish | Flat / fading | 0.006% / -0.013% / 0.013% | Position building in range | 55.4% | 18.1% | 26.5% | 3.10x | 0.133% / 0.229% |
| 2025-07-12 14:15 | 2.87x | Full-bodied bearish | Flat / fading | 0.071% / 0.083% / 0.026% | Position building in range | 90.3% | 0.0% | 9.7% | 3.29x | 0.013% / 0.090% |
| 2025-07-12 16:45 | 6.29x | Bullish pin-bar / lower rejection | Flat / fading | -0.032% / 0.019% / 0.045% | Position building in range | 46.7% | 10.0% | 43.3% | 3.02x | 0.071% / 0.045% |
| 2025-07-13 11:00 | 2.55x | Full-bodied bearish | Impulse / continuation | -0.199% / -0.199% / -0.443% | True breakout | 61.9% | 19.0% | 19.0% | 1.76x | 0.482% / 0.006% |
| 2025-07-13 11:15 | 6.42x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.077% / -0.328% | True breakout | 68.3% | 9.8% | 22.0% | 3.63x | 0.419% / 0.000% |
| 2025-07-13 11:45 | 3.93x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.168% / -0.251% / -0.116% | True breakout | 26.8% | 2.4% | 70.7% | 3.10x | 0.342% / 0.006% |
| 2025-07-13 14:00 | 9.87x | Full-bodied bearish | Flat / fading | 0.058% / 0.091% / 0.240% | Weak move without breakout | 93.8% | 0.0% | 6.2% | 3.44x | 0.052% / 0.260% |
| 2025-07-14 07:00 | 21.55x | Small-body bullish | Reversal | -0.369% / -0.279% / -0.214% | Liquidity sweep / reversal | 37.0% | 38.0% | 25.0% | 5.30x | 0.071% / 0.493% |
| 2025-07-14 07:15 | 6.18x | Full-bodied bearish | Flat / fading | 0.091% / 0.319% / -0.143% | Weak move without breakout | 66.7% | 11.5% | 21.8% | 3.81x | 0.143% / 0.325% |
| 2025-07-14 07:30 | 6.67x | Bearish pin-bar / upper rejection | Reversal | 0.227% / 0.065% / -0.123% | Liquidity sweep / reversal | 19.0% | 46.6% | 34.5% | 2.04x | 0.234% / 0.325% |
| 2025-07-14 08:15 | 2.78x | Full-bodied bearish | Reversal | 0.111% / 0.300% / 0.560% | Liquidity sweep / reversal | 97.9% | 2.1% | 0.0% | 1.36x | 0.091% / 0.606% |
| 2025-07-14 09:00 | 3.05x | Bearish pin-bar / upper rejection | Reversal | 0.397% / 0.878% / 1.795% | Liquidity sweep / reversal | 37.3% | 56.9% | 5.9% | 1.32x | 0.007% / 2.595% |
| 2025-07-14 09:30 | 4.43x | Full-bodied bullish | Impulse / continuation | 0.877% / 0.909% / 1.876% | True breakout | 70.5% | 23.8% | 5.7% | 2.30x | 1.921% / 0.058% |
| 2025-07-14 09:45 | 10.56x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.032% / 0.888% / 1.643% | True breakout | 49.5% | 46.9% | 3.7% | 5.24x | 1.790% / 0.121% |
| 2025-07-14 10:00 | 5.04x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.856% / 0.958% / 1.182% | True breakout | 6.9% | 66.7% | 26.4% | 1.02x | 1.757% / 0.000% |
| 2025-07-14 10:15 | 5.85x | Full-bodied bullish | Impulse / continuation | 0.101% / 0.748% / 0.532% | True breakout | 95.7% | 4.3% | 0.0% | 1.86x | 0.893% / 0.165% |
| 2025-07-14 10:30 | 5.24x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.646% / 0.222% / 0.095% | True breakout | 32.7% | 14.3% | 53.1% | 0.61x | 0.791% / 0.095% |
| 2025-07-14 10:45 | 5.61x | Full-bodied bullish | Flat / fading | -0.421% / -0.214% / -0.377% | Position building in range | 72.1% | 16.4% | 11.4% | 1.81x | 0.075% / 0.591% |
| 2025-07-14 11:00 | 3.03x | Full-bodied bearish | Flat / fading | 0.208% / -0.126% / 0.290% | Weak move without breakout | 87.3% | 12.7% | 0.0% | 0.98x | 0.171% / 0.410% |
| 2025-07-14 18:00 | 2.73x | Full-bodied bullish | Impulse / continuation | 0.964% / 0.901% / 1.638% | True breakout | 82.3% | 0.0% | 17.7% | 3.90x | 1.714% / 0.422% |
| 2025-07-14 18:15 | 8.52x | Full-bodied bullish | Impulse / continuation | -0.062% / 0.000% / 0.980% | True breakout | 70.0% | 3.1% | 26.9% | 3.32x | 1.142% / 0.187% |
| 2025-07-14 19:00 | 3.12x | Full-bodied bullish | Flat / fading | 0.310% / -0.074% / -0.229% | Weak move without breakout | 83.6% | 9.4% | 7.0% | 1.70x | 0.471% / 0.229% |
| 2025-07-14 19:15 | 2.66x | Full-bodied bullish | Reversal | -0.383% / -0.371% / -0.649% | Liquidity sweep / reversal | 67.1% | 32.9% | 0.0% | 0.98x | 0.019% / 0.748% |
| 2025-07-15 09:30 | 2.83x | Doji / upper rejection | Impulse / continuation | 0.142% / -0.136% / -0.179% | True breakout | 0.0% | 80.0% | 20.0% | 1.03x | 0.296% / 0.296% |
| 2025-07-15 10:45 | 2.60x | Full-bodied bearish | Reversal | 0.068% / 0.235% / 0.656% | Liquidity sweep / reversal | 62.3% | 18.8% | 18.8% | 1.87x | 0.031% / 0.718% |
| 2025-07-15 11:30 | 3.54x | Full-bodied bullish | Impulse / continuation | -0.025% / 0.264% / 1.347% | True breakout | 92.3% | 7.7% | 0.0% | 2.03x | 1.371% / 0.148% |
| 2025-07-15 12:30 | 5.53x | Full-bodied bullish | Impulse / continuation | 0.910% / 0.673% / 0.655% | True breakout | 97.8% | 2.2% | 0.0% | 3.78x | 1.165% / 0.140% |
| 2025-07-15 12:45 | 7.21x | Full-bodied bullish | Flat / fading | -0.234% / -0.162% / -0.168% | Position building in range | 69.8% | 19.5% | 10.7% | 3.67x | 0.222% / 0.463% |
| 2025-07-15 13:00 | 2.97x | Bearish pin-bar / upper rejection | Flat / fading | 0.072% / -0.018% / -0.096% | Weak move without breakout | 51.3% | 48.7% | 0.0% | 1.07x | 0.229% / 0.301% |
| 2025-07-15 23:30 | 3.34x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.127% / 0.121% / 0.042% | True breakout | 21.4% | 57.1% | 21.4% | 1.06x | 0.211% / 0.006% |
| 2025-07-16 07:00 | 3.73x | Bearish pin-bar / upper rejection | Reversal | -0.060% / -0.012% / 0.097% | Liquidity sweep / reversal | 3.2% | 54.8% | 41.9% | 2.49x | 0.060% / 0.151% |
| 2025-07-16 08:30 | 3.64x | Full-bodied bullish | Flat / fading | -0.018% / -0.114% / -0.174% | Weak move without breakout | 79.2% | 20.8% | 0.0% | 3.04x | 0.048% / 0.283% |
| 2025-07-16 09:00 | 3.02x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.066% / -0.060% / -0.217% | True breakout | 44.4% | 11.1% | 44.4% | 1.90x | 0.223% / 0.042% |
| 2025-07-16 10:00 | 3.27x | Full-bodied bearish | Impulse / continuation | -0.084% / -0.296% / -0.271% | True breakout | 72.1% | 25.6% | 2.3% | 1.81x | 0.597% / 0.036% |
| 2025-07-16 10:15 | 5.05x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.211% / -0.308% / 0.356% | False breakout | 30.4% | 13.0% | 56.5% | 1.82x | 0.513% / 0.465% |
| 2025-07-16 10:30 | 2.85x | Full-bodied bearish | Impulse -> reversal | -0.097% / 0.024% / 0.363% | False breakout | 89.7% | 5.1% | 5.1% | 1.37x | 0.302% / 0.678% |
| 2025-07-16 10:45 | 5.84x | Bullish pin-bar / lower rejection | Reversal | 0.121% / 0.666% / 0.351% | Liquidity sweep / reversal | 24.6% | 23.1% | 52.3% | 2.24x | 0.030% / 0.775% |
| 2025-07-16 11:15 | 3.45x | Full-bodied bullish | Impulse / continuation | -0.205% / -0.313% / 0.217% | True breakout | 78.3% | 15.7% | 6.1% | 3.35x | 0.415% / 0.427% |
| 2025-07-16 12:15 | 3.15x | Full-bodied bullish | Impulse / continuation | 0.108% / 0.444% / 0.786% | True breakout | 61.8% | 30.0% | 8.2% | 2.45x | 0.954% / 0.060% |
| 2025-07-16 13:00 | 2.48x | Full-bodied bullish | Flat / fading | -0.024% / 0.060% / -0.149% | Weak move without breakout | 82.4% | 5.4% | 12.2% | 1.36x | 0.143% / 0.333% |
| 2025-07-17 10:00 | 7.98x | Bearish pin-bar / upper rejection | Flat / fading | 0.024% / 0.024% / -0.060% | Weak move without breakout | 40.5% | 42.9% | 16.7% | 4.69x | 0.233% / 0.090% |
| 2025-07-17 10:15 | 3.36x | Bearish pin-bar / upper rejection | Reversal | 0.000% / 0.144% / -0.006% | Liquidity sweep / reversal | 11.1% | 48.1% | 40.7% | 1.16x | 0.209% / 0.120% |
| 2025-07-17 10:45 | 2.89x | Full-bodied bullish | Reversal | -0.227% / -0.149% / -0.335% | Liquidity sweep / reversal | 69.4% | 30.6% | 0.0% | 1.45x | 0.012% / 0.448% |
| 2025-07-17 12:00 | 2.81x | Bullish pin-bar / lower rejection | Reversal | 0.042% / 0.048% / 0.138% | Liquidity sweep / reversal | 3.0% | 9.1% | 87.9% | 1.02x | 0.066% / 0.174% |
| 2025-07-18 09:00 | 3.57x | Full-bodied bullish | Reversal | -0.164% / -0.267% / 0.492% | Liquidity sweep / reversal | 80.6% | 6.5% | 12.9% | 1.09x | 0.850% / 0.388% |
| 2025-07-18 10:00 | 12.36x | Full-bodied bullish | Impulse / continuation | -0.024% / 0.453% / 0.199% | True breakout | 68.4% | 30.1% | 1.5% | 6.49x | 0.586% / 0.266% |
| 2025-07-18 10:15 | 4.26x | Bullish pin-bar / lower rejection | Reversal | 0.477% / 0.163% / 0.586% | Liquidity sweep / reversal | 7.3% | 20.0% | 72.7% | 1.31x | 0.024% / 0.755% |
| 2025-07-18 10:30 | 3.82x | Full-bodied bullish | Flat / fading | -0.313% / -0.252% / 0.204% | Weak move without breakout | 76.2% | 21.0% | 2.9% | 2.31x | 0.295% / 0.391% |
| 2025-07-18 11:15 | 2.95x | Full-bodied bullish | Flat / fading | 0.096% / 0.078% / -0.054% | Weak move without breakout | 64.8% | 30.8% | 4.4% | 1.81x | 0.378% / 0.084% |
| 2025-07-18 11:45 | 2.62x | Bearish pin-bar / upper rejection | Reversal | 0.072% / -0.132% / -0.066% | Liquidity sweep / reversal | 5.9% | 92.2% | 2.0% | 0.94x | 0.216% / 0.156% |
| 2025-07-19 10:00 | 2.72x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.120% / 0.418% / 0.191% | True breakout | 42.0% | 10.0% | 48.0% | 3.27x | 0.628% / 0.042% |
| 2025-07-19 10:30 | 5.91x | Full-bodied bullish | Impulse / continuation | -0.065% / -0.226% / -0.208% | True breakout | 69.3% | 18.7% | 12.0% | 4.12x | 0.208% / 0.238% |
| 2025-07-19 10:45 | 2.60x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.161% / -0.089% / -0.054% | True breakout | 16.0% | 76.0% | 8.0% | 2.17x | 0.173% / 0.006% |
| 2025-07-19 17:45 | 5.24x | Bullish pin-bar / lower rejection | Reversal | 0.018% / 0.036% / 0.012% | Liquidity sweep / reversal | 26.7% | 26.7% | 46.7% | 3.18x | 0.024% / 0.042% |
| 2025-07-20 10:00 | 7.52x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.018% / 0.042% | True breakout | 80.0% | 6.7% | 13.3% | 3.68x | 0.143% / 0.119% |
| 2025-07-20 10:15 | 5.44x | Bullish pin-bar / lower rejection | Reversal | -0.018% / 0.078% / -0.012% | Liquidity sweep / reversal | 4.0% | 4.0% | 92.0% | 2.52x | 0.119% / 0.089% |
| 2025-07-20 17:30 | 2.64x | Bearish pin-bar / upper rejection | Reversal | 0.000% / 0.006% / -0.054% | Liquidity sweep / reversal | 57.1% | 42.9% | 0.0% | 1.46x | 0.024% / 0.083% |
| 2025-07-20 18:30 | 5.55x | Bullish pin-bar / lower rejection | Reversal | 0.024% / 0.161% / 0.328% | Liquidity sweep / reversal | 58.3% | 0.0% | 41.7% | 2.62x | 0.006% / 0.394% |
| 2025-07-21 07:00 | 18.77x | Full-bodied bullish | Impulse / continuation | 0.048% / 0.024% / 0.208% | True breakout | 66.0% | 18.0% | 16.0% | 7.87x | 0.268% / 0.065% |
| 2025-07-21 07:15 | 7.30x | Small-body bullish | Impulse / continuation | -0.024% / 0.048% / 0.268% | True breakout | 26.7% | 36.7% | 36.7% | 3.13x | 0.476% / 0.071% |
| 2025-07-21 07:30 | 2.68x | Bullish pin-bar / lower rejection | Reversal | 0.071% / 0.184% / 0.452% | Liquidity sweep / reversal | 18.8% | 31.3% | 50.0% | 1.41x | 0.036% / 0.500% |
| 2025-07-21 08:00 | 5.42x | Full-bodied bullish | Impulse -> reversal | 0.107% / 0.267% / -0.119% | False breakout | 61.3% | 32.3% | 6.5% | 2.30x | 0.315% / 0.285% |
| 2025-07-21 08:15 | 6.40x | Bearish pin-bar / upper rejection | Reversal | 0.160% / 0.172% / -0.053% | Liquidity sweep / reversal | 34.5% | 63.6% | 1.8% | 3.55x | 0.184% / 0.391% |
| 2025-07-21 08:45 | 2.71x | Bullish pin-bar / lower rejection | Reversal | -0.397% / -0.225% / -0.255% | Liquidity sweep / reversal | 13.0% | 8.7% | 78.3% | 1.06x | 0.012% / 0.563% |
| 2025-07-21 09:00 | 8.96x | Full-bodied bearish | Flat / fading | 0.172% / 0.113% / 0.107% | Position building in range | 69.1% | 2.1% | 28.9% | 4.24x | 0.024% / 0.333% |
| 2025-07-21 09:15 | 4.01x | Full-bodied bullish | Flat / fading | -0.059% / -0.030% / -0.125% | Weak move without breakout | 88.2% | 11.8% | 0.0% | 1.16x | 0.160% / 0.350% |
| 2025-07-21 10:00 | 3.54x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.059% / -0.184% / -0.410% | True breakout | 5.0% | 58.3% | 36.7% | 1.76x | 0.469% / 0.036% |
| 2025-07-22 10:00 | 3.66x | Bearish pin-bar / upper rejection | Reversal | 0.012% / -0.065% / -0.119% | Liquidity sweep / reversal | 3.2% | 48.4% | 48.4% | 1.59x | 0.125% / 0.208% |
| 2025-07-22 10:15 | 4.78x | Bearish pin-bar / upper rejection | Reversal | -0.077% / -0.167% / -0.238% | Liquidity sweep / reversal | 9.5% | 90.5% | 0.0% | 1.00x | 0.042% / 0.244% |
| 2025-07-22 10:45 | 3.33x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.036% / -0.072% / -0.197% | True breakout | 40.0% | 60.0% | 0.0% | 1.84x | 0.358% / 0.125% |
| 2025-07-22 11:30 | 5.04x | Full-bodied bearish | Impulse / continuation | 0.084% / -0.197% / 0.173% | True breakout | 70.8% | 2.1% | 27.1% | 2.14x | 0.317% / 0.287% |
| 2025-07-22 12:00 | 3.10x | Full-bodied bearish | Reversal | 0.132% / 0.371% / 0.461% | Liquidity sweep / reversal | 73.8% | 6.2% | 20.0% | 2.72x | 0.120% / 0.575% |
| 2025-07-22 12:15 | 2.61x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.239% / 0.413% / 0.407% | True breakout | 48.8% | 2.3% | 48.8% | 1.56x | 0.473% / 0.042% |
| 2025-07-22 12:30 | 3.56x | Full-bodied bullish | Flat / fading | 0.173% / 0.090% / 0.185% | Weak move without breakout | 62.1% | 28.8% | 9.1% | 2.21x | 0.233% / 0.030% |
| 2025-07-22 18:00 | 2.74x | Full-bodied bearish | Reversal | 0.102% / 0.162% / 0.006% | Liquidity sweep / reversal | 60.9% | 15.2% | 23.9% | 2.09x | 0.030% / 0.234% |
| 2025-07-23 07:00 | 4.70x | Bullish pin-bar / lower rejection | Flat / fading | -0.048% / -0.042% / -0.090% | Weak move without breakout | 38.1% | 0.0% | 61.9% | 1.66x | 0.102% / 0.030% |
| 2025-07-23 08:30 | 2.68x | Full-bodied bullish | Reversal | -0.078% / -0.030% / -0.030% | Liquidity sweep / reversal | 90.9% | 0.0% | 9.1% | 0.72x | 0.000% / 0.203% |
| 2025-07-23 09:45 | 6.43x | Full-bodied bullish | Impulse / continuation | 0.083% / 0.292% / 0.292% | True breakout | 83.3% | 8.3% | 8.3% | 2.31x | 0.364% / 0.006% |
| 2025-07-23 10:00 | 6.02x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.209% / 0.107% / 0.179% | True breakout | 40.0% | 57.1% | 2.9% | 2.03x | 0.298% / 0.030% |
| 2025-07-23 10:15 | 3.62x | Full-bodied bullish | Flat / fading | -0.101% / 0.000% / -0.024% | Weak move without breakout | 67.3% | 23.1% | 9.6% | 2.82x | 0.089% / 0.190% |
| 2025-07-23 10:30 | 3.69x | Bullish pin-bar / lower rejection | Flat / fading | 0.101% / 0.071% / 0.024% | Weak move without breakout | 54.8% | 0.0% | 45.2% | 1.47x | 0.089% / 0.190% |
| 2025-07-23 11:00 | 3.10x | Bullish pin-bar / lower rejection | Flat / fading | 0.006% / -0.048% / -0.095% | Weak move without breakout | 16.7% | 38.9% | 44.4% | 1.55x | 0.137% / 0.030% |
| 2025-07-23 12:30 | 2.59x | Full-bodied bearish | Impulse / continuation | -0.125% / -0.316% / -0.292% | True breakout | 67.4% | 14.0% | 18.6% | 1.59x | 0.519% / 0.072% |
| 2025-07-23 13:00 | 2.39x | Full-bodied bearish | Flat / fading | -0.126% / 0.024% / -0.042% | Weak move without breakout | 62.5% | 18.8% | 18.8% | 1.60x | 0.204% / 0.102% |
| 2025-07-23 13:15 | 2.36x | Small-body bearish | Reversal | 0.150% / 0.192% / 0.234% | Liquidity sweep / reversal | 48.0% | 26.0% | 26.0% | 1.53x | 0.024% / 0.324% |
| 2025-07-23 19:00 | 3.05x | Full-bodied bearish | Impulse / continuation | -0.036% / -0.179% / -0.168% | True breakout | 61.2% | 32.7% | 6.1% | 1.87x | 0.305% / 0.000% |
| 2025-07-24 10:00 | 2.70x | Small-body bullish | Reversal | -0.078% / -0.287% / -0.574% | Liquidity sweep / reversal | 30.4% | 39.1% | 30.4% | 1.47x | 0.024% / 0.682% |
| 2025-07-24 10:15 | 2.54x | Small-body bearish | Impulse / continuation | -0.210% / -0.228% / -0.587% | True breakout | 35.7% | 25.0% | 39.3% | 1.69x | 0.653% / 0.018% |
| 2025-07-24 10:30 | 7.71x | Full-bodied bearish | Impulse / continuation | -0.018% / -0.288% / -0.636% | True breakout | 67.3% | 5.8% | 26.9% | 2.97x | 0.660% / 0.078% |
| 2025-07-24 10:45 | 5.18x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.270% / -0.360% / -0.264% | True breakout | 18.2% | 30.3% | 51.5% | 1.89x | 0.642% / 0.006% |
| 2025-07-24 11:00 | 4.70x | Full-bodied bearish | Impulse / continuation | -0.090% / -0.349% / -0.181% | True breakout | 68.7% | 3.1% | 28.1% | 3.42x | 0.373% / 0.024% |
| 2025-07-24 11:15 | 3.01x | Small-body bearish | Impulse -> reversal | -0.259% / 0.096% / -0.024% | False breakout | 50.0% | 13.3% | 36.7% | 1.36x | 0.283% / 0.108% |
| 2025-07-24 11:30 | 3.35x | Full-bodied bearish | Reversal | 0.356% / 0.169% / 0.242% | Liquidity sweep / reversal | 89.6% | 2.1% | 8.3% | 2.04x | -0.030% / 0.368% |
| 2025-07-24 13:15 | 3.41x | Full-bodied bearish | Flat / fading | 0.145% / 0.309% / -0.145% | Weak move without breakout | 92.8% | 4.8% | 2.4% | 2.35x | 0.212% / 0.315% |
| 2025-07-25 07:00 | 4.80x | Full-bodied bullish | Flat / fading | -0.030% / -0.054% / -0.096% | Position building in range | 71.4% | 17.1% | 11.4% | 3.66x | 0.030% / 0.313% |
| 2025-07-25 07:30 | 2.85x | Bullish pin-bar / lower rejection | Flat / fading | -0.127% / -0.042% / -0.072% | Position building in range | 8.2% | 4.1% | 87.8% | 2.22x | 0.181% / 0.006% |
| 2025-07-25 10:00 | 4.65x | Bullish pin-bar / lower rejection | Flat / fading | -0.006% / -0.151% / -0.085% | Position building in range | 25.0% | 10.3% | 64.7% | 3.00x | 0.212% / 0.030% |
| 2025-07-25 12:30 | 2.76x | Full-bodied bearish | Reversal | 0.103% / -0.055% / 0.456% | Liquidity sweep / reversal | 81.0% | 1.2% | 17.9% | 3.25x | 0.189% / 1.333% |
| 2025-07-25 13:15 | 3.52x | Full-bodied bullish | Impulse / continuation | -0.079% / 0.127% / 0.024% | True breakout | 90.7% | 1.9% | 7.5% | 2.95x | 0.793% / 0.720% |
| 2025-07-25 13:30 | 17.92x | Bearish pin-bar / upper rejection | Reversal | 0.206% / -0.085% / -0.073% | Liquidity sweep / reversal | 5.6% | 52.0% | 42.4% | 6.08x | 0.273% / 0.436% |
| 2025-07-25 13:45 | 4.42x | Bearish pin-bar / upper rejection | Reversal | -0.290% / -0.103% / -0.296% | Liquidity sweep / reversal | 41.7% | 45.2% | 13.1% | 1.55x | 0.133% / 0.478% |
| 2025-07-26 15:45 | 12.64x | Small-body bearish | Flat / fading | 0.025% / 0.031% / 0.006% | Position building in range | 55.6% | 7.4% | 37.0% | 10.22x | 0.031% / 0.099% |
| 2025-07-26 17:45 | 2.77x | Full-bodied bullish | Impulse / continuation | 0.080% / 0.080% / 0.000% | True breakout | 92.9% | 7.1% | 0.0% | 1.29x | 0.086% / 0.031% |
| 2025-07-27 10:30 | 2.84x | Full-bodied bearish | Flat / fading | 0.000% / -0.043% / 0.130% | Weak move without breakout | 90.0% | 0.0% | 10.0% | 2.58x | 0.062% / 0.148% |
| 2025-07-27 17:45 | 4.54x | Full-bodied bullish | Flat / fading | -0.019% / -0.019% / 0.006% | Position building in range | 68.7% | 31.3% | 0.0% | 2.17x | 0.006% / 0.043% |
| 2025-07-27 18:00 | 2.89x | Full-bodied bearish | Reversal | 0.000% / 0.012% / 0.062% | Liquidity sweep / reversal | 66.7% | 0.0% | 33.3% | 0.72x | 0.025% / 0.062% |
| 2025-07-28 07:00 | 30.69x | Bearish pin-bar / upper rejection | Reversal | -0.012% / 0.012% / 0.167% | Liquidity sweep / reversal | 3.4% | 52.5% | 44.1% | 8.43x | 0.185% / 0.148% |
| 2025-07-28 07:15 | 3.43x | Bullish pin-bar / lower rejection | Reversal | 0.025% / -0.025% / 0.414% | Liquidity sweep / reversal | 8.3% | 0.0% | 91.7% | 2.23x | 0.062% / 0.451% |
| 2025-07-28 08:00 | 4.21x | Full-bodied bullish | Impulse / continuation | 0.234% / 0.419% / 0.259% | True breakout | 88.9% | 8.3% | 2.8% | 2.63x | 0.635% / -0.012% |
| 2025-07-28 08:15 | 5.27x | Full-bodied bullish | Impulse / continuation | 0.184% / 0.258% / -0.061% | True breakout | 85.7% | 14.3% | 0.0% | 2.65x | 0.400% / 0.117% |
| 2025-07-28 08:30 | 8.26x | Bearish pin-bar / upper rejection | Reversal | 0.074% / -0.160% / -0.282% | Liquidity sweep / reversal | 43.5% | 50.7% | 5.8% | 3.74x | 0.215% / 0.374% |
| 2025-07-28 09:00 | 4.68x | Full-bodied bearish | Flat / fading | -0.086% / -0.123% / -0.141% | Weak move without breakout | 65.1% | 17.5% | 17.5% | 2.53x | 0.215% / 0.178% |
| 2025-07-28 09:45 | 2.76x | Small-body bullish | Reversal | -0.184% / -0.215% / -0.270% | Liquidity sweep / reversal | 41.9% | 35.5% | 22.6% | 2.01x | 0.086% / 0.418% |
| 2025-07-28 10:00 | 3.14x | Full-bodied bearish | Impulse / continuation | -0.031% / -0.142% / 0.074% | True breakout | 68.2% | 31.8% | 0.0% | 1.27x | 0.234% / 0.160% |
| 2025-07-28 10:15 | 2.52x | Bearish pin-bar / upper rejection | Reversal | -0.111% / -0.055% / -0.012% | Liquidity sweep / reversal | 8.2% | 55.1% | 36.7% | 1.31x | 0.203% / 0.228% |
| 2025-07-28 10:45 | 2.38x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.160% / 0.043% / 0.450% | True breakout | 29.0% | 22.6% | 48.4% | 0.79x | 0.548% / 0.062% |
| 2025-07-28 11:00 | 2.34x | Small-body bullish | Impulse / continuation | -0.117% / -0.080% / 0.258% | True breakout | 53.2% | 27.7% | 19.1% | 1.19x | 0.387% / 0.221% |
| 2025-07-28 11:45 | 2.85x | Full-bodied bullish | Flat / fading | -0.031% / 0.006% / -0.074% | Position building in range | 76.9% | 20.5% | 2.6% | 1.78x | 0.098% / 0.110% |
| 2025-07-28 14:45 | 2.72x | Full-bodied bearish | Impulse / continuation | -0.530% / -0.831% / -1.164% | True breakout | 73.3% | 16.7% | 10.0% | 2.66x | 1.404% / 0.006% |
| 2025-07-28 15:00 | 4.48x | Full-bodied bearish | Impulse / continuation | -0.303% / -0.495% / -1.182% | True breakout | 74.8% | 0.9% | 24.3% | 3.12x | 1.418% / 0.142% |
| 2025-07-28 15:15 | 2.97x | Small-body bearish | Impulse / continuation | -0.192% / -0.335% / -0.851% | True breakout | 52.1% | 22.9% | 25.0% | 2.27x | 1.211% / 0.075% |
| 2025-07-28 15:30 | 3.39x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.143% / -0.691% / -0.715% | True breakout | 36.4% | 19.5% | 44.2% | 1.77x | 1.020% / 0.062% |
| 2025-07-28 15:45 | 2.36x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.548% / -0.517% / -0.511% | True breakout | 30.6% | 15.3% | 54.2% | 1.52x | 0.878% / 0.199% |
| 2025-07-28 16:00 | 4.33x | Small-body bearish | Flat / fading | 0.031% / -0.025% / -0.144% | Weak move without breakout | 54.4% | 21.5% | 24.1% | 3.13x | 0.332% / 0.207% |
| 2025-07-28 16:15 | 3.72x | Bullish pin-bar / lower rejection | Reversal | -0.056% / 0.006% / -0.194% | Liquidity sweep / reversal | 4.7% | 32.6% | 62.8% | 1.43x | 0.100% / 0.326% |
| 2025-07-29 09:00 | 2.51x | Small-body bearish | Reversal | 0.006% / 0.100% / 0.320% | Liquidity sweep / reversal | 45.5% | 36.4% | 18.2% | 1.50x | 0.088% / 0.703% |
| 2025-07-29 10:00 | 7.61x | Bearish pin-bar / upper rejection | Reversal | -0.282% / -0.150% / -0.313% | Liquidity sweep / reversal | 9.2% | 70.1% | 20.7% | 2.46x | 0.013% / 0.745% |
| 2025-07-29 10:45 | 3.45x | Small-body bearish | Reversal | 0.214% / 0.598% / 0.290% | Liquidity sweep / reversal | 59.4% | 5.9% | 34.7% | 2.55x | 0.113% / 0.673% |
| 2025-07-29 20:30 | 6.45x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.347% / -0.486% / -0.783% | True breakout | 41.6% | 10.9% | 47.4% | 7.58x | 0.877% / 0.032% |
| 2025-07-29 20:45 | 2.81x | Full-bodied bearish | Impulse / continuation | -0.139% / -0.260% / -0.215% | True breakout | 90.6% | 3.1% | 6.3% | 2.46x | 0.532% / 0.114% |
| 2025-07-29 21:00 | 7.23x | Bullish pin-bar / lower rejection | Flat / fading | -0.120% / -0.298% / 0.044% | Position building in range | 22.5% | 16.7% | 60.8% | 3.48x | 0.311% / 0.133% |
| 2025-07-30 09:45 | 2.78x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.353% / -0.560% / -0.390% | True breakout | 43.6% | 46.2% | 10.3% | 1.36x | 0.668% / 0.000% |
| 2025-07-30 10:00 | 4.51x | Full-bodied bearish | Impulse / continuation | -0.209% / -0.139% / 0.120% | True breakout | 80.0% | 0.0% | 20.0% | 2.28x | 0.316% / 0.126% |
| 2025-07-30 10:15 | 3.65x | Full-bodied bearish | Reversal | 0.070% / 0.171% / 0.108% | Liquidity sweep / reversal | 75.0% | 2.3% | 22.7% | 1.30x | 0.108% / 0.424% |
| 2025-07-30 10:30 | 3.26x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.101% / 0.259% / -0.070% | True breakout | 38.2% | 17.6% | 44.1% | 0.96x | 0.354% / 0.089% |
| 2025-07-30 16:30 | 3.14x | Small-body bearish | Reversal | 0.064% / 0.344% / 0.217% | Liquidity sweep / reversal | 55.6% | 9.3% | 35.2% | 1.96x | 0.019% / 0.414% |
| 2025-07-30 17:00 | 3.47x | Full-bodied bullish | Flat / fading | -0.063% / -0.127% / -0.089% | Position building in range | 80.0% | 20.0% | 0.0% | 1.86x | 0.025% / 0.159% |
| 2025-07-31 09:15 | 3.21x | Small-body bullish | Impulse / continuation | 0.019% / 0.070% / 0.000% | True breakout | 31.6% | 36.8% | 31.6% | 2.41x | 0.526% / 0.178% |
| 2025-07-31 09:45 | 2.72x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.285% / -0.070% / -0.120% | False breakout | 29.2% | 41.7% | 29.2% | 1.31x | 0.456% / 0.247% |
| 2025-07-31 10:00 | 14.10x | Small-body bullish | Reversal | -0.354% / -0.468% / -0.474% | Liquidity sweep / reversal | 57.3% | 36.0% | 6.7% | 3.89x | 0.019% / 0.531% |
| 2025-07-31 10:15 | 7.02x | Full-bodied bearish | Flat / fading | -0.114% / -0.051% / -0.140% | Weak move without breakout | 64.4% | 3.4% | 32.2% | 3.60x | 0.323% / 0.108% |
| 2025-08-01 07:00 | 7.86x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.070% / 0.133% / 0.240% | True breakout | 16.3% | 60.5% | 23.3% | 3.54x | 0.386% / 0.051% |
| 2025-08-01 07:30 | 4.20x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.221% / 0.107% / -0.050% | True breakout | 32.3% | 64.5% | 3.2% | 2.10x | 0.252% / 0.050% |
| 2025-08-01 10:00 | 3.75x | Bearish pin-bar / upper rejection | Reversal | -0.019% / 0.057% / 0.082% | Liquidity sweep / reversal | 1.7% | 70.7% | 27.6% | 2.22x | 0.208% / 0.094% |
| 2025-08-01 14:15 | 2.17x | Small-body bearish | Impulse / continuation | -0.076% / -0.354% / -0.329% | True breakout | 52.4% | 11.9% | 35.7% | 1.88x | 0.430% / -0.013% |
| 2025-08-01 14:30 | 2.21x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.278% / -0.247% / -0.291% | True breakout | 27.3% | 3.0% | 69.7% | 1.43x | 0.354% / 0.025% |
| 2025-08-01 14:45 | 2.61x | Full-bodied bearish | Impulse / continuation | 0.032% / 0.025% / -0.209% | True breakout | 75.9% | 6.9% | 17.2% | 2.39x | 0.279% / 0.108% |
| 2025-08-01 19:45 | 4.63x | Full-bodied bearish | Impulse / continuation | 0.262% / 0.275% / 0.434% | True breakout | 78.4% | 1.5% | 20.1% | 7.92x | 0.287% / 0.473% |
| 2025-08-01 20:00 | 3.35x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.013% / 0.159% / 0.198% | True breakout | 45.6% | 4.4% | 50.0% | 3.66x | 0.217% / 0.089% |
| 2025-08-04 07:00 | 2.65x | Small-body bullish | Reversal | -0.019% / -0.070% / -0.044% | Liquidity sweep / reversal | 42.1% | 36.8% | 21.1% | 1.77x | 0.013% / 0.146% |
| 2025-08-04 10:00 | 3.81x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.025% / 0.165% / 0.196% | True breakout | 6.9% | 51.7% | 41.4% | 1.37x | 0.266% / 0.076% |
| 2025-08-04 10:30 | 4.33x | Small-body bullish | Flat / fading | -0.089% / 0.032% / 0.057% | Position building in range | 57.1% | 38.1% | 4.8% | 2.19x | 0.082% / 0.145% |
| 2025-08-04 12:15 | 3.81x | Full-bodied bullish | Flat / fading | 0.063% / 0.076% / -0.019% | Weak move without breakout | 77.4% | 22.6% | 0.0% | 1.46x | 0.139% / 0.051% |
| 2025-08-04 17:30 | 2.89x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.088% / 0.384% | True breakout | 77.1% | 17.1% | 5.7% | 2.23x | 0.528% / 0.038% |
| 2025-08-04 17:45 | 3.48x | Bearish pin-bar / upper rejection | Reversal | 0.088% / 0.428% / 0.365% | Liquidity sweep / reversal | 2.1% | 85.1% | 12.8% | 2.76x | 0.000% / 0.528% |
| 2025-08-04 18:15 | 3.78x | Full-bodied bullish | Flat / fading | -0.044% / -0.063% / 0.031% | Position building in range | 75.0% | 22.2% | 2.8% | 3.56x | 0.081% / 0.094% |
| 2025-08-05 07:00 | 3.91x | Bullish pin-bar / lower rejection | Reversal | -0.044% / 0.006% / 0.019% | Liquidity sweep / reversal | 4.8% | 26.2% | 69.0% | 1.79x | 0.075% / 0.062% |
| 2025-08-05 10:30 | 5.41x | Full-bodied bullish | Flat / fading | -0.130% / -0.167% / -0.093% | Weak move without breakout | 84.0% | 6.7% | 9.3% | 3.52x | 0.056% / 0.211% |
| 2025-08-05 10:45 | 2.74x | Small-body bearish | Flat / fading | -0.037% / 0.074% / 0.031% | Weak move without breakout | 58.8% | 29.4% | 11.8% | 1.44x | 0.081% / 0.161% |
| 2025-08-05 12:00 | 3.23x | Full-bodied bearish | Impulse / continuation | -0.417% / -0.261% / -0.199% | True breakout | 93.5% | 0.0% | 6.5% | 2.19x | 0.598% / 0.031% |
| 2025-08-05 12:15 | 3.09x | Full-bodied bearish | Flat / fading | 0.156% / -0.044% / 0.150% | Weak move without breakout | 80.7% | 6.0% | 13.3% | 2.59x | 0.181% / 0.350% |
| 2025-08-06 09:15 | 2.82x | Bearish pin-bar / upper rejection | Reversal | -0.012% / -0.031% / -0.050% | Liquidity sweep / reversal | 28.6% | 61.9% | 9.5% | 1.40x | 0.099% / 0.105% |
| 2025-08-06 10:00 | 5.36x | Bearish pin-bar / upper rejection | Reversal | -0.062% / -0.279% / -0.279% | Liquidity sweep / reversal | 31.0% | 48.3% | 20.7% | 1.92x | 0.050% / 0.403% |
| 2025-08-06 10:15 | 3.46x | Small-body bearish | Impulse / continuation | -0.217% / -0.167% / -0.124% | True breakout | 37.0% | 29.6% | 33.3% | 1.65x | 0.341% / 0.050% |
| 2025-08-06 10:30 | 7.22x | Small-body bearish | Flat / fading | 0.050% / 0.000% / 0.081% | Position building in range | 58.7% | 9.5% | 31.7% | 3.54x | 0.124% / 0.143% |
| 2025-08-06 11:45 | 3.17x | Bullish pin-bar / lower rejection | Flat / fading | 0.093% / 0.062% / 0.068% | Position building in range | 44.8% | 0.0% | 55.2% | 2.57x | 0.044% / 0.143% |
| 2025-08-06 16:45 | 2.67x | Small-body bearish | Impulse / continuation | -0.118% / -0.311% / -0.317% | True breakout | 44.1% | 17.6% | 38.2% | 1.46x | 0.441% / 0.323% |
| 2025-08-06 17:00 | 5.03x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.193% / -0.025% / -0.311% | True breakout | 25.0% | 68.4% | 6.6% | 3.18x | 0.348% / 0.124% |
| 2025-08-06 17:15 | 4.61x | Small-body bearish | Flat / fading | 0.168% / -0.006% / 0.156% | Weak move without breakout | 41.7% | 29.2% | 29.2% | 2.56x | 0.156% / 0.224% |
| 2025-08-06 20:00 | 5.03x | Full-bodied bullish | Impulse / continuation | 0.321% / 0.154% / 0.450% | True breakout | 76.0% | 18.4% | 5.6% | 4.15x | 0.574% / 0.068% |
| 2025-08-06 20:15 | 3.16x | Small-body bullish | Flat / fading | -0.166% / -0.012% / 0.197% | Position building in range | 49.0% | 39.4% | 11.5% | 1.89x | 0.252% / 0.320% |
| 2025-08-06 21:45 | 2.94x | Full-bodied bullish | Impulse / continuation | -0.085% / -0.024% / -0.315% | True breakout | 98.4% | 0.0% | 1.6% | 4.25x | 0.539% / 0.897% |
| 2025-08-06 22:00 | 3.39x | Bullish pin-bar / lower rejection | Reversal | 0.061% / 0.358% / -0.764% | Liquidity sweep / reversal | 8.8% | 0.7% | 90.5% | 2.09x | 0.892% / 0.625% |
| 2025-08-06 22:15 | 2.88x | Bearish pin-bar / upper rejection | Reversal | 0.297% / -0.291% / -0.491% | Liquidity sweep / reversal | 8.7% | 80.9% | 10.4% | 1.43x | 0.394% / 0.952% |
| 2025-08-06 22:30 | 2.50x | Bullish pin-bar / lower rejection | Reversal | -0.586% / -1.118% / -0.895% | Liquidity sweep / reversal | 39.3% | 13.1% | 47.5% | 1.39x | 0.000% / 1.245% |
| 2025-08-07 10:30 | 2.95x | Full-bodied bullish | Impulse / continuation | -0.085% / 1.463% / 1.797% | True breakout | 85.6% | 4.4% | 10.0% | 2.28x | 1.949% / 0.170% |
| 2025-08-07 11:00 | 12.67x | Full-bodied bullish | Impulse / continuation | -0.060% / 0.329% / 0.934% | True breakout | 89.5% | 10.5% | 0.0% | 7.82x | 1.526% / 0.209% |
| 2025-08-07 11:15 | 4.25x | Bearish pin-bar / upper rejection | Reversal | 0.389% / 0.946% / 0.940% | Liquidity sweep / reversal | 7.1% | 63.5% | 29.4% | 1.54x | 0.024% / 1.587% |
| 2025-08-07 11:30 | 3.06x | Full-bodied bullish | Impulse / continuation | 0.555% / 0.602% / 0.101% | True breakout | 72.3% | 26.6% | 1.1% | 1.58x | 1.193% / 0.060% |
| 2025-08-07 11:45 | 5.94x | Bearish pin-bar / upper rejection | Reversal | 0.047% / -0.006% / -0.617% | Liquidity sweep / reversal | 46.7% | 47.2% | 6.2% | 3.05x | 0.635% / 0.682% |
| 2025-08-07 23:15 | 2.76x | Bearish pin-bar / upper rejection | Flat / fading | 0.139% / 0.295% / 0.187% | Weak move without breakout | 58.4% | 41.6% | 0.0% | 3.56x | 0.536% / 0.120% |
| 2025-08-08 10:00 | 3.34x | Small-body bearish | Impulse / continuation | -0.078% / -0.205% / -0.350% | True breakout | 34.6% | 28.8% | 36.5% | 1.64x | 0.452% / 0.048% |
| 2025-08-08 13:30 | 3.13x | Full-bodied bullish | Impulse / continuation | -0.018% / 0.006% / 0.260% | True breakout | 62.0% | 38.0% | 0.0% | 1.99x | 0.302% / 0.066% |
| 2025-08-08 14:45 | 3.28x | Small-body bullish | Reversal | -0.120% / -0.018% / -0.354% | Liquidity sweep / reversal | 59.3% | 39.5% | 1.2% | 3.96x | 0.132% / 0.372% |
| 2025-08-08 17:00 | 3.71x | Bearish pin-bar / upper rejection | Flat / fading | 0.102% / 0.175% / 0.217% | Weak move without breakout | 23.9% | 63.3% | 12.8% | 2.78x | 0.596% / 0.090% |
| 2025-08-08 17:45 | 2.79x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.018% / 0.000% / 0.096% | True breakout | 11.8% | 35.3% | 52.9% | 0.73x | 0.397% / 0.054% |
| 2025-08-08 18:00 | 2.46x | Bearish pin-bar / upper rejection | Reversal | -0.018% / 0.060% / 0.078% | Liquidity sweep / reversal | 3.0% | 95.5% | 1.5% | 1.36x | 0.174% / 0.072% |
| 2025-08-08 23:15 | 8.14x | Full-bodied bullish | Impulse / continuation | 0.395% / 0.682% / 0.873% | True breakout | 77.5% | 15.3% | 7.2% | 3.98x | 1.142% / 0.191% |
| 2025-08-08 23:30 | 9.59x | Small-body bullish | Impulse / continuation | 0.286% / 0.744% / 0.727% | True breakout | 49.6% | 26.3% | 24.1% | 3.91x | 0.744% / 0.006% |
| 2025-08-11 07:30 | 2.68x | Bearish pin-bar / upper rejection | Flat / fading | 0.065% / -0.160% / 0.018% | Weak move without breakout | 21.1% | 53.5% | 25.4% | 1.38x | 0.219% / 0.166% |
| 2025-08-11 10:00 | 2.64x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.047% / -0.142% / -0.142% | True breakout | 21.7% | 75.0% | 3.3% | 1.43x | 0.367% / 0.083% |
| 2025-08-11 18:30 | 3.23x | Full-bodied bearish | Impulse / continuation | 0.120% / 0.108% / -0.090% | True breakout | 97.6% | 0.8% | 1.6% | 3.74x | 0.433% / 0.301% |
| 2025-08-12 07:30 | 4.44x | Full-bodied bearish | Flat / fading | 0.000% / 0.151% / 0.200% | Position building in range | 62.3% | 0.0% | 37.7% | 4.54x | 0.145% / 0.200% |
| 2025-08-12 10:00 | 4.28x | Bearish pin-bar / upper rejection | Reversal | 0.271% / 0.114% / 0.006% | Liquidity sweep / reversal | 10.0% | 78.3% | 11.7% | 1.53x | 0.024% / 0.301% |
| 2025-08-13 07:00 | 2.79x | Bearish pin-bar / upper rejection | Flat / fading | -0.048% / -0.066% / -0.030% | Weak move without breakout | 23.3% | 50.0% | 26.7% | 2.46x | 0.072% / 0.066% |
| 2025-08-13 09:00 | 2.87x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.090% / 0.108% / 0.150% | True breakout | 50.0% | 0.0% | 50.0% | 1.22x | 0.168% / 0.006% |
| 2025-08-13 09:15 | 3.35x | Full-bodied bullish | Flat / fading | 0.018% / 0.060% / -0.072% | Weak move without breakout | 72.7% | 27.3% | 0.0% | 1.62x | 0.078% / 0.072% |
| 2025-08-13 10:00 | 2.74x | Bullish pin-bar / lower rejection | Reversal | -0.132% / -0.221% / -0.150% | Liquidity sweep / reversal | 7.7% | 23.1% | 69.2% | 0.85x | 0.006% / 0.353% |
| 2025-08-13 10:15 | 3.39x | Full-bodied bearish | Impulse / continuation | -0.090% / -0.054% / -0.084% | True breakout | 95.7% | 4.3% | 0.0% | 1.50x | 0.222% / 0.018% |
| 2025-08-13 10:45 | 2.51x | Bearish pin-bar / upper rejection | Reversal | 0.036% / -0.030% / 0.042% | Liquidity sweep / reversal | 36.8% | 63.2% | 0.0% | 1.20x | 0.072% / 0.168% |
| 2025-08-13 11:00 | 3.44x | Bullish pin-bar / lower rejection | Reversal | -0.066% / -0.090% / 0.000% | Liquidity sweep / reversal | 15.0% | 15.0% | 70.0% | 2.52x | 0.036% / 0.156% |
| 2025-08-13 17:00 | 2.64x | Bearish pin-bar / upper rejection | Reversal | -0.048% / -0.018% / 0.006% | Liquidity sweep / reversal | 17.5% | 55.0% | 27.5% | 1.64x | 0.132% / 0.138% |
| 2025-08-13 17:15 | 2.74x | Bearish pin-bar / upper rejection | Reversal | 0.030% / 0.102% / 0.162% | Liquidity sweep / reversal | 13.3% | 53.3% | 33.3% | 1.74x | 0.024% / 0.180% |
| 2025-08-14 10:15 | 3.39x | Small-body bearish | Reversal | 0.054% / 0.067% / 0.145% | Liquidity sweep / reversal | 41.2% | 23.5% | 35.3% | 1.29x | 0.060% / 0.200% |
| 2025-08-14 11:45 | 6.19x | Full-bodied bearish | Flat / fading | 0.085% / 0.261% / 0.206% | Weak move without breakout | 67.1% | 1.4% | 31.4% | 2.49x | 0.061% / 0.418% |
| 2025-08-14 21:15 | 3.40x | Bearish pin-bar / upper rejection | Flat / fading | 0.036% / -0.012% / -0.042% | Position building in range | 54.7% | 43.7% | 1.6% | 3.64x | 0.120% / 0.066% |
| 2025-08-15 10:00 | 7.12x | Bearish pin-bar / upper rejection | Flat / fading | -0.048% / -0.024% / -0.006% | Weak move without breakout | 38.9% | 46.3% | 14.8% | 2.98x | 0.090% / 0.006% |
| 2025-08-15 13:00 | 3.42x | Full-bodied bullish | Impulse / continuation | 0.334% / 0.209% / 0.227% | True breakout | 66.0% | 21.3% | 12.8% | 2.34x | 0.411% / 0.078% |
| 2025-08-15 13:15 | 5.41x | Full-bodied bullish | Flat / fading | -0.125% / -0.196% / -0.107% | Position building in range | 67.1% | 15.9% | 17.1% | 3.67x | 0.030% / 0.261% |
| 2025-08-15 15:15 | 2.64x | Small-body bearish | Reversal | 0.173% / 0.268% / 0.292% | Liquidity sweep / reversal | 55.8% | 37.7% | 6.5% | 2.76x | 0.030% / 0.387% |
| 2025-08-16 10:00 | 4.05x | Bullish pin-bar / lower rejection | Reversal | 0.424% / 0.388% / 0.309% | Liquidity sweep / reversal | 25.8% | 0.5% | 73.7% | 4.31x | 0.091% / 0.636% |
| 2025-08-17 15:45 | 3.65x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.121% / -0.127% / -0.097% | True breakout | 8.3% | 0.0% | 91.7% | 2.13x | 0.229% / -0.018% |
| 2025-08-17 16:00 | 8.37x | Bullish pin-bar / lower rejection | Flat / fading | -0.006% / -0.042% / -0.024% | Position building in range | 34.3% | 14.3% | 51.4% | 5.70x | 0.048% / 0.072% |
| 2025-08-18 07:00 | 20.95x | Full-bodied bullish | Impulse / continuation | -0.054% / 0.054% / 0.475% | True breakout | 71.3% | 0.9% | 27.8% | 7.79x | 0.619% / 0.126% |
| 2025-08-18 07:30 | 2.55x | Full-bodied bullish | Impulse / continuation | 0.114% / 0.421% / 0.288% | True breakout | 84.6% | 15.4% | 0.0% | 1.34x | 0.565% / 0.054% |
| 2025-08-18 07:45 | 4.58x | Small-body bullish | Impulse / continuation | 0.306% / 0.228% / 0.228% | True breakout | 45.2% | 33.3% | 21.4% | 2.09x | 0.450% / -0.006% |
| 2025-08-18 08:00 | 5.69x | Full-bodied bullish | Reversal | -0.078% / -0.132% / -0.353% | Liquidity sweep / reversal | 67.6% | 32.4% | 0.0% | 3.37x | 0.066% / 0.353% |
| 2025-08-18 09:00 | 2.85x | Full-bodied bearish | Impulse / continuation | 0.180% / -0.174% / -0.180% | True breakout | 100.0% | 0.0% | 0.0% | 1.49x | 0.204% / 0.192% |
| 2025-08-18 09:30 | 3.64x | Full-bodied bearish | Flat / fading | 0.108% / -0.006% / 0.114% | Weak move without breakout | 89.4% | 3.0% | 7.6% | 1.92x | 0.090% / 0.259% |
| 2025-08-18 10:15 | 2.97x | Bearish pin-bar / upper rejection | Reversal | 0.150% / 0.217% / 0.277% | Liquidity sweep / reversal | 8.6% | 75.9% | 15.5% | 1.41x | 0.054% / 0.277% |
| 2025-08-18 15:30 | 4.15x | Full-bodied bullish | Impulse / continuation | 0.311% / 0.622% / 0.772% | True breakout | 93.8% | 3.1% | 3.1% | 3.26x | 0.874% / 0.012% |
| 2025-08-18 15:45 | 5.77x | Full-bodied bullish | Impulse / continuation | 0.310% / 0.430% / 0.453% | True breakout | 78.3% | 21.7% | 0.0% | 2.93x | 0.561% / 0.000% |
| 2025-08-18 16:15 | 2.64x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.030% / 0.024% / 0.386% | True breakout | 27.0% | 29.7% | 43.2% | 2.43x | 0.505% / 0.095% |
| 2025-08-18 17:00 | 4.39x | Bearish pin-bar / upper rejection | Reversal | 0.213% / -0.148% / -0.231% | Liquidity sweep / reversal | 34.1% | 63.6% | 2.3% | 2.47x | 0.510% / 0.415% |
| 2025-08-18 17:30 | 2.44x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.107% / -0.083% / -0.131% | True breakout | 54.0% | 44.2% | 1.8% | 2.59x | 0.333% / 0.107% |
| 2025-08-18 21:45 | 3.15x | Full-bodied bullish | Impulse / continuation | 0.236% / 0.088% / 0.171% | True breakout | 72.5% | 18.8% | 8.7% | 4.63x | 0.507% / 0.242% |
| 2025-08-18 22:00 | 5.49x | Small-body bullish | Flat / fading | -0.147% / -0.182% / -0.106% | Position building in range | 31.5% | 36.2% | 32.3% | 2.93x | 0.200% / 0.435% |
| 2025-08-18 22:15 | 3.30x | Bullish pin-bar / lower rejection | Flat / fading | -0.035% / 0.082% / -0.094% | Position building in range | 25.9% | 28.7% | 45.4% | 2.24x | 0.153% / 0.318% |
| 2025-08-19 10:00 | 3.65x | Bearish pin-bar / upper rejection | Flat / fading | -0.023% / 0.227% / -0.012% | Position building in range | 45.9% | 53.2% | 0.9% | 2.64x | 0.331% / 0.099% |
| 2025-08-19 18:00 | 2.52x | Full-bodied bearish | Impulse / continuation | -0.100% / -0.148% / -0.225% | True breakout | 89.0% | 7.6% | 3.4% | 3.21x | 0.266% / 0.071% |
| 2025-08-20 07:00 | 2.74x | Bullish pin-bar / lower rejection | Reversal | 0.012% / 0.006% / 0.241% | Liquidity sweep / reversal | 7.4% | 14.8% | 77.8% | 5.35x | 0.059% / 0.388% |
| 2025-08-20 10:00 | 3.05x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.176% / 0.105% | Liquidity sweep / reversal | 44.1% | 14.7% | 41.2% | 1.14x | 0.141% / 0.258% |
| 2025-08-20 10:30 | 3.16x | Full-bodied bullish | Flat / fading | -0.134% / -0.070% / 0.035% | Weak move without breakout | 62.5% | 8.3% | 29.2% | 1.42x | 0.088% / 0.158% |
| 2025-08-20 12:00 | 2.98x | Bearish pin-bar / upper rejection | Flat / fading | -0.099% / -0.105% / -0.029% | Weak move without breakout | 17.0% | 66.0% | 17.0% | 1.68x | 0.199% / 0.023% |
| 2025-08-20 14:00 | 3.31x | Small-body bearish | Impulse / continuation | -0.247% / -0.100% / -0.012% | True breakout | 39.1% | 29.7% | 31.2% | 2.13x | 0.306% / 0.165% |
| 2025-08-20 14:15 | 2.75x | Small-body bearish | Reversal | 0.147% / 0.306% / 0.130% | Liquidity sweep / reversal | 52.5% | 35.0% | 12.5% | 2.56x | 0.018% / 0.395% |
| 2025-08-21 07:00 | 4.40x | Bearish pin-bar / upper rejection | Flat / fading | 0.182% / 0.176% / 0.047% | Weak move without breakout | 21.2% | 75.0% | 3.8% | 3.96x | 0.264% / 0.000% |
| 2025-08-21 08:45 | 4.24x | Full-bodied bullish | Reversal | -0.117% / -0.134% / -0.310% | Liquidity sweep / reversal | 69.4% | 18.4% | 12.2% | 2.33x | 0.076% / 0.362% |
| 2025-08-21 09:00 | 3.29x | Small-body bearish | Impulse / continuation | -0.018% / 0.000% / -0.234% | True breakout | 48.8% | 31.7% | 19.5% | 1.72x | 0.579% / 0.099% |
| 2025-08-21 09:45 | 3.64x | Full-bodied bearish | Impulse / continuation | -0.041% / -0.199% / -0.387% | True breakout | 75.0% | 4.5% | 20.5% | 1.67x | 0.492% / 0.311% |
| 2025-08-21 10:00 | 9.91x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.158% / -0.217% / -0.592% | True breakout | 8.1% | 23.3% | 68.6% | 3.13x | 0.756% / 0.352% |
| 2025-08-21 10:15 | 6.02x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.059% / -0.188% / -0.241% | True breakout | 29.8% | 62.8% | 7.4% | 2.88x | 0.599% / 0.270% |
| 2025-08-21 10:45 | 3.27x | Small-body bearish | Impulse / continuation | -0.247% / -0.053% / -0.018% | True breakout | 36.7% | 33.3% | 30.0% | 1.51x | 0.412% / 0.088% |
| 2025-08-21 11:00 | 3.15x | Bullish pin-bar / lower rejection | Reversal | 0.195% / 0.171% / 0.401% | Liquidity sweep / reversal | 60.0% | 0.0% | 40.0% | 1.71x | 0.100% / 0.401% |
| 2025-08-22 09:00 | 3.36x | Bearish pin-bar / upper rejection | Reversal | 0.100% / -0.006% / -0.030% | Liquidity sweep / reversal | 15.4% | 42.3% | 42.3% | 1.11x | 0.148% / 0.124% |
| 2025-08-22 09:30 | 3.16x | Small-body bearish | Flat / fading | -0.053% / -0.024% / -0.089% | Weak move without breakout | 51.4% | 14.3% | 34.3% | 1.49x | 0.201% / 0.100% |
| 2025-08-22 11:30 | 4.06x | Bearish pin-bar / upper rejection | Flat / fading | -0.130% / -0.159% / 0.059% | Position building in range | 53.1% | 43.8% | 3.1% | 2.45x | 0.124% / 0.212% |
| 2025-08-22 13:15 | 2.63x | Full-bodied bullish | Reversal | -0.041% / -0.165% / -0.306% | Liquidity sweep / reversal | 82.2% | 11.1% | 6.7% | 1.38x | 0.029% / 0.364% |
| 2025-08-22 16:30 | 2.25x | Small-body bearish | Reversal | 0.118% / 0.184% / -0.047% | Liquidity sweep / reversal | 52.7% | 25.5% | 21.8% | 1.77x | 0.148% / 0.414% |
| 2025-08-23 18:45 | 4.66x | Bullish pin-bar / lower rejection | Reversal | -0.053% / -0.177% / -0.171% | Liquidity sweep / reversal | 12.5% | 37.5% | 50.0% | 2.11x | -0.053% / 0.230% |
| 2025-08-24 10:00 | 5.47x | Full-bodied bearish | Impulse / continuation | -0.012% / 0.006% / -0.107% | True breakout | 95.5% | 0.0% | 4.5% | 4.89x | 0.142% / 0.018% |
| 2025-08-24 10:15 | 3.17x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.018% / -0.024% / -0.071% | True breakout | 41.7% | 0.0% | 58.3% | 2.10x | 0.130% / 0.030% |
| 2025-08-24 10:30 | 3.16x | Small-body bullish | Reversal | -0.041% / -0.112% / -0.041% | Liquidity sweep / reversal | 50.0% | 16.7% | 33.3% | 1.91x | 0.006% / 0.148% |
| 2025-08-24 10:45 | 5.23x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.071% / -0.047% / -0.047% | True breakout | 36.8% | 5.3% | 57.9% | 2.83x | 0.107% / 0.036% |
| 2025-08-24 11:00 | 5.32x | Small-body bearish | Flat / fading | 0.024% / 0.071% / 0.059% | Weak move without breakout | 60.0% | 10.0% | 30.0% | 2.50x | 0.030% / 0.107% |
| 2025-08-24 11:30 | 3.59x | Small-body bullish | Flat / fading | -0.047% / -0.012% / -0.018% | Position building in range | 47.1% | 35.3% | 17.6% | 1.83x | 0.036% / 0.047% |
| 2025-08-24 11:45 | 2.93x | Bearish pin-bar / upper rejection | Reversal | 0.036% / 0.053% / 0.036% | Liquidity sweep / reversal | 57.1% | 42.9% | 0.0% | 1.37x | 0.000% / 0.059% |
| 2025-08-25 07:00 | 25.99x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.018% / -0.095% / -0.077% | True breakout | 22.9% | 45.7% | 31.4% | 6.81x | 0.136% / 0.006% |
| 2025-08-25 07:45 | 2.86x | Bearish pin-bar / upper rejection | Reversal | 0.047% / 0.142% / 0.142% | Liquidity sweep / reversal | 50.0% | 42.9% | 7.1% | 1.62x | 0.012% / 0.213% |
| 2025-08-25 08:15 | 4.80x | Small-body bullish | Reversal | -0.012% / 0.000% / -0.101% | Liquidity sweep / reversal | 59.3% | 33.3% | 7.4% | 2.66x | 0.071% / 0.112% |
| 2025-08-25 08:30 | 3.14x | Bearish pin-bar / upper rejection | Reversal | 0.012% / -0.053% / -0.053% | Liquidity sweep / reversal | 15.0% | 70.0% | 15.0% | 1.70x | 0.041% / 0.136% |
| 2025-08-25 09:15 | 2.50x | Bearish pin-bar / upper rejection | Reversal | 0.036% / 0.036% / -0.184% | Liquidity sweep / reversal | 33.3% | 66.7% | 0.0% | 1.06x | 0.231% / 0.101% |
| 2025-08-25 09:30 | 3.04x | Bullish pin-bar / lower rejection | Reversal | 0.000% / -0.024% / -0.184% | Liquidity sweep / reversal | 31.3% | 12.5% | 56.3% | 1.07x | 0.065% / 0.266% |
| 2025-08-25 10:00 | 5.24x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.195% / -0.160% / -0.255% | True breakout | 20.0% | 55.0% | 25.0% | 1.22x | 0.391% / 0.041% |
| 2025-08-25 10:15 | 7.17x | Full-bodied bearish | Impulse / continuation | 0.036% / -0.101% / -0.095% | True breakout | 68.7% | 14.6% | 16.7% | 2.74x | 0.196% / 0.095% |
| 2025-08-25 10:30 | 3.49x | Bearish pin-bar / upper rejection | Reversal | -0.136% / -0.095% / -0.403% | Liquidity sweep / reversal | 16.7% | 41.7% | 41.7% | 1.22x | 0.000% / 0.457% |
| 2025-08-25 11:00 | 3.67x | Bullish pin-bar / lower rejection | Reversal | -0.036% / -0.309% / -0.178% | Liquidity sweep / reversal | 25.0% | 17.9% | 57.1% | 1.42x | 0.006% / 0.362% |
| 2025-08-25 11:30 | 5.83x | Full-bodied bearish | Flat / fading | 0.113% / 0.131% / 0.018% | Position building in range | 81.8% | 1.8% | 16.4% | 2.56x | 0.012% / 0.208% |
| 2025-08-25 11:45 | 2.58x | Full-bodied bullish | Flat / fading | 0.018% / 0.065% / -0.113% | Weak move without breakout | 65.6% | 34.4% | 0.0% | 1.31x | 0.095% / 0.113% |
| 2025-08-26 07:00 | 2.93x | Bearish pin-bar / upper rejection | Flat / fading | 0.036% / 0.107% / 0.071% | Weak move without breakout | 44.8% | 55.2% | 0.0% | 2.92x | 0.107% / -0.012% |
| 2025-08-26 09:00 | 2.62x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.238% / 0.232% / 0.452% | True breakout | 16.7% | 16.7% | 66.7% | 1.45x | 0.475% / 0.006% |
| 2025-08-26 09:15 | 6.40x | Full-bodied bullish | Impulse / continuation | -0.006% / 0.036% / 0.125% | True breakout | 90.9% | 6.8% | 2.3% | 3.33x | 0.261% / 0.059% |
| 2025-08-26 09:30 | 4.38x | Doji / upper rejection | Impulse / continuation | 0.042% / 0.219% / 0.154% | True breakout | 0.0% | 69.0% | 31.0% | 1.97x | 0.267% / 0.267% |
| 2025-08-26 10:00 | 6.05x | Full-bodied bullish | Flat / fading | -0.089% / -0.065% / -0.083% | Weak move without breakout | 77.8% | 11.1% | 11.1% | 2.24x | 0.047% / 0.201% |
| 2025-08-27 07:00 | 4.64x | Bearish pin-bar / upper rejection | Flat / fading | 0.024% / 0.041% / 0.065% | Position building in range | 4.8% | 66.7% | 28.6% | 1.99x | 0.065% / 0.006% |
| 2025-08-27 09:15 | 2.50x | Full-bodied bearish | Reversal | 0.083% / 0.000% / 0.201% | Liquidity sweep / reversal | 64.7% | 5.9% | 29.4% | 1.65x | 0.006% / 0.284% |
| 2025-08-27 10:00 | 2.67x | Full-bodied bullish | Impulse / continuation | 0.124% / 0.124% / 0.260% | True breakout | 68.4% | 26.3% | 5.3% | 1.63x | 0.384% / 0.000% |
| 2025-08-27 10:15 | 8.37x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.154% / 0.171% | True breakout | 60.0% | 40.0% | 0.0% | 2.90x | 0.260% / 0.053% |
| 2025-08-27 10:45 | 3.35x | Full-bodied bullish | Impulse / continuation | -0.018% / 0.018% / 0.024% | True breakout | 100.0% | 0.0% | 0.0% | 1.93x | 0.106% / 0.100% |
| 2025-08-27 11:00 | 4.56x | Bearish pin-bar / upper rejection | Reversal | 0.035% / -0.041% / 0.006% | Liquidity sweep / reversal | 10.0% | 60.0% | 30.0% | 2.07x | 0.083% / 0.100% |
| 2025-08-27 14:45 | 2.53x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / 0.012% / 0.094% | Weak move without breakout | 28.0% | 68.0% | 4.0% | 1.09x | 0.153% / 0.018% |
| 2025-08-28 07:00 | 4.32x | Bearish pin-bar / upper rejection | Flat / fading | -0.059% / -0.018% / -0.059% | Weak move without breakout | 1.6% | 68.9% | 29.5% | 4.72x | 0.124% / 0.053% |
| 2025-08-28 10:30 | 2.51x | Doji / lower rejection | Impulse / continuation | -0.018% / 0.100% / 0.083% | True breakout | 0.0% | 16.7% | 83.3% | 0.82x | 0.171% / 0.171% |
| 2025-08-28 12:00 | 3.70x | Bullish pin-bar / lower rejection | Flat / fading | -0.029% / -0.006% / 0.000% | Weak move without breakout | 32.1% | 17.9% | 50.0% | 1.71x | 0.059% / 0.059% |
| 2025-08-28 17:30 | 2.60x | Small-body bullish | Impulse / continuation | 0.012% / 0.159% / 0.094% | True breakout | 58.3% | 20.8% | 20.8% | 1.49x | 0.218% / 0.024% |
| 2025-08-28 18:00 | 3.95x | Full-bodied bullish | Flat / fading | -0.106% / -0.065% / -0.118% | Weak move without breakout | 67.6% | 27.0% | 5.4% | 2.24x | 0.035% / 0.241% |
| 2025-08-28 20:00 | 7.64x | Full-bodied bearish | Impulse / continuation | 0.195% / -0.225% / -0.189% | True breakout | 66.9% | 6.5% | 26.6% | 7.00x | 0.503% / 0.231% |
| 2025-08-28 20:30 | 7.01x | Bullish pin-bar / lower rejection | Flat / fading | 0.059% / 0.036% / 0.113% | Position building in range | 59.8% | 0.0% | 40.2% | 4.06x | 0.214% / 0.160% |
| 2025-08-28 20:45 | 2.82x | Bullish pin-bar / lower rejection | Flat / fading | -0.024% / -0.018% / 0.130% | Weak move without breakout | 14.0% | 19.3% | 66.7% | 1.58x | 0.154% / 0.166% |
| 2025-08-29 10:00 | 2.93x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.130% / -0.148% / -0.101% | True breakout | 19.4% | 64.5% | 16.1% | 1.92x | 0.261% / 0.053% |
| 2025-08-29 10:15 | 6.97x | Small-body bearish | Flat / fading | -0.018% / 0.053% / -0.012% | Weak move without breakout | 46.8% | 19.1% | 34.0% | 2.71x | 0.130% / 0.113% |
| 2025-08-29 10:45 | 4.48x | Bullish pin-bar / lower rejection | Flat / fading | -0.024% / -0.065% / -0.018% | Weak move without breakout | 32.5% | 22.5% | 45.0% | 2.15x | 0.059% / 0.160% |
| 2025-08-29 13:30 | 4.54x | Full-bodied bearish | Impulse / continuation | -0.143% / -0.167% / -0.470% | True breakout | 62.0% | 3.8% | 34.2% | 3.21x | 0.595% / 0.030% |
| 2025-08-29 14:30 | 3.78x | Full-bodied bearish | Flat / fading | -0.012% / 0.054% / 0.114% | Position building in range | 75.9% | 0.0% | 24.1% | 3.22x | 0.054% / 0.144% |
| 2025-08-30 15:15 | 3.67x | Bullish pin-bar / lower rejection | Flat / fading | -0.012% / -0.012% / -0.018% | Position building in range | 20.0% | 20.0% | 60.0% | 1.32x | 0.018% / 0.000% |
| 2025-08-30 17:00 | 3.87x | Full-bodied bearish | Impulse / continuation | -0.048% / -0.120% / -0.222% | True breakout | 72.7% | 9.1% | 18.2% | 3.21x | 0.240% / 0.000% |
| 2025-08-30 17:30 | 2.89x | Full-bodied bearish | Impulse / continuation | -0.006% / -0.102% / -0.072% | True breakout | 72.2% | 0.0% | 27.8% | 4.20x | 0.120% / 0.000% |
| 2025-08-30 18:45 | 3.95x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.066% / 0.012% / 0.216% | True breakout | 48.3% | 48.3% | 3.4% | 4.19x | 0.282% / 0.006% |
| 2025-08-31 11:30 | 3.27x | Full-bodied bullish | Flat / fading | 0.030% / -0.030% / -0.018% | Weak move without breakout | 75.0% | 25.0% | 0.0% | 1.04x | 0.060% / 0.078% |
| 2025-08-31 18:30 | 7.95x | Full-bodied bearish | Reversal | 0.012% / 0.120% / 0.294% | Liquidity sweep / reversal | 61.9% | 19.0% | 19.0% | 5.35x | 0.024% / 0.324% |
| 2025-09-01 07:00 | 21.63x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.120% / 0.209% / 0.168% | True breakout | 20.9% | 58.1% | 20.9% | 6.69x | 0.323% / 0.018% |
| 2025-09-01 07:15 | 4.54x | Full-bodied bullish | Impulse / continuation | 0.090% / 0.185% / 0.066% | True breakout | 83.3% | 4.2% | 12.5% | 2.56x | 0.203% / 0.036% |
| 2025-09-01 07:30 | 3.93x | Small-body bullish | Flat / fading | 0.096% / -0.042% / 0.012% | Weak move without breakout | 40.0% | 40.0% | 20.0% | 3.25x | 0.113% / 0.078% |
| 2025-09-01 09:15 | 5.15x | Full-bodied bullish | Reversal | -0.095% / -0.065% / -0.262% | Liquidity sweep / reversal | 71.7% | 25.0% | 3.3% | 2.94x | 0.030% / 0.357% |
| 2025-09-01 10:45 | 2.72x | Bearish pin-bar / upper rejection | Flat / fading | 0.024% / -0.066% / 0.036% | Weak move without breakout | 30.8% | 41.0% | 28.2% | 1.39x | 0.096% / 0.072% |
| 2025-09-01 18:00 | 2.66x | Bullish pin-bar / lower rejection | Flat / fading | -0.120% / -0.090% / -0.006% | Position building in range | 34.9% | 7.0% | 58.1% | 2.33x | 0.150% / 0.012% |
| 2025-09-02 09:30 | 3.19x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.024% / -0.270% / -0.318% | True breakout | 46.5% | 0.0% | 53.5% | 2.25x | 0.552% / 0.054% |
| 2025-09-02 10:00 | 10.97x | Bullish pin-bar / lower rejection | Flat / fading | 0.054% / -0.048% / -0.199% | Weak move without breakout | 51.0% | 0.0% | 49.0% | 4.53x | 0.361% / 0.150% |
| 2025-09-02 10:15 | 2.60x | Bullish pin-bar / lower rejection | Reversal | -0.102% / -0.229% / -0.223% | Liquidity sweep / reversal | 35.5% | 19.4% | 45.2% | 1.14x | 0.096% / 0.415% |
| 2025-09-02 11:00 | 4.52x | Bullish pin-bar / lower rejection | Reversal | 0.030% / 0.121% / 0.078% | Liquidity sweep / reversal | 13.9% | 11.1% | 75.0% | 1.16x | 0.084% / 0.181% |
| 2025-09-02 15:45 | 2.59x | Bullish pin-bar / lower rejection | Flat / fading | -0.248% / -0.054% / -0.060% | Weak move without breakout | 37.7% | 18.9% | 43.4% | 1.81x | 0.272% / 0.109% |
| 2025-09-02 16:00 | 2.53x | Full-bodied bearish | Flat / fading | 0.194% / 0.042% / 0.212% | Weak move without breakout | 69.5% | 30.5% | 0.0% | 1.93x | 0.024% / 0.309% |
| 2025-09-02 21:45 | 3.06x | Full-bodied bullish | Impulse / continuation | 0.091% / 0.309% / 0.315% | True breakout | 96.7% | 0.0% | 3.3% | 1.16x | 0.412% / 0.085% |
| 2025-09-03 09:45 | 2.62x | Full-bodied bullish | Impulse -> reversal | -0.060% / -0.428% / -0.368% | False breakout | 89.2% | 2.7% | 8.1% | 2.11x | 0.133% / 0.579% |
| 2025-09-03 10:00 | 4.72x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.368% / -0.392% / -0.482% | True breakout | 31.3% | 68.7% | 0.0% | 1.62x | 0.579% / 0.030% |
| 2025-09-03 10:15 | 9.32x | Full-bodied bearish | Flat / fading | -0.024% / 0.061% / -0.139% | Weak move without breakout | 69.2% | 3.3% | 27.5% | 4.35x | 0.212% / 0.097% |
| 2025-09-03 16:15 | 3.24x | Full-bodied bullish | Reversal | 0.030% / -0.224% / -0.157% | Liquidity sweep / reversal | 69.4% | 27.8% | 2.8% | 2.24x | 0.091% / 0.302% |
| 2025-09-03 16:30 | 2.62x | Doji / upper rejection | Impulse / continuation | -0.254% / -0.151% / -0.145% | True breakout | 0.0% | 62.5% | 37.5% | 0.92x | 0.332% / 0.332% |
| 2025-09-03 16:45 | 4.89x | Full-bodied bearish | Flat / fading | 0.103% / 0.067% / 0.182% | Position building in range | 64.6% | 15.4% | 20.0% | 3.79x | -0.012% / 0.254% |
| 2025-09-03 19:00 | 3.11x | Small-body bullish | Flat / fading | 0.085% / 0.066% / 0.078% | Weak move without breakout | 59.3% | 25.9% | 14.8% | 1.20x | 0.127% / 0.091% |
| 2025-09-03 19:15 | 4.30x | Full-bodied bullish | Flat / fading | -0.018% / -0.018% / -0.036% | Weak move without breakout | 60.0% | 28.0% | 12.0% | 1.07x | 0.042% / 0.175% |
| 2025-09-04 09:45 | 4.16x | Full-bodied bullish | Impulse / continuation | 0.144% / 0.156% / 0.168% | True breakout | 69.0% | 3.4% | 27.6% | 2.14x | 0.247% / 0.084% |
| 2025-09-04 10:00 | 8.34x | Small-body bullish | Flat / fading | 0.012% / 0.000% / -0.072% | Position building in range | 41.8% | 30.9% | 27.3% | 3.67x | 0.102% / 0.108% |
| 2025-09-04 10:30 | 2.98x | Bearish pin-bar / upper rejection | Reversal | 0.024% / -0.072% / -0.096% | Liquidity sweep / reversal | 15.0% | 70.0% | 15.0% | 1.01x | 0.156% / 0.042% |
| 2025-09-04 15:15 | 4.04x | Small-body bearish | Impulse / continuation | -0.030% / -0.156% / 0.078% | True breakout | 54.3% | 11.4% | 34.3% | 2.04x | 0.192% / 0.078% |
| 2025-09-04 15:45 | 2.80x | Full-bodied bearish | Reversal | 0.114% / 0.235% / 0.337% | Liquidity sweep / reversal | 75.0% | 7.1% | 17.9% | 1.56x | 0.036% / 0.403% |
| 2025-09-05 09:00 | 2.77x | Bearish pin-bar / upper rejection | Reversal | -0.042% / -0.006% / -0.072% | Liquidity sweep / reversal | 53.8% | 46.2% | 0.0% | 1.25x | 0.018% / 0.156% |
| 2025-09-05 10:00 | 4.95x | Bullish pin-bar / lower rejection | Flat / fading | -0.036% / -0.090% / -0.012% | Weak move without breakout | 22.7% | 13.6% | 63.6% | 2.32x | 0.114% / 0.030% |
| 2025-09-05 10:15 | 2.61x | Small-body bearish | Impulse / continuation | -0.054% / -0.006% / 0.024% | True breakout | 46.2% | 38.5% | 15.4% | 1.21x | 0.078% / 0.054% |
| 2025-09-05 11:45 | 9.19x | Full-bodied bullish | Flat / fading | -0.066% / -0.036% / -0.042% | Weak move without breakout | 80.0% | 18.2% | 1.8% | 5.07x | 0.120% / 0.102% |
| 2025-09-05 12:00 | 3.73x | Bearish pin-bar / upper rejection | Flat / fading | 0.030% / 0.036% / 0.006% | Weak move without breakout | 31.4% | 57.1% | 11.4% | 2.43x | 0.036% / 0.090% |
| 2025-09-05 23:30 | 4.17x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.078% / -0.066% / -0.060% | True breakout | 4.3% | 17.4% | 78.3% | 2.60x | 0.162% / 0.006% |
| 2025-09-07 10:15 | 2.92x | Small-body bullish | Reversal | -0.006% / -0.006% / -0.006% | Liquidity sweep / reversal | 50.0% | 25.0% | 25.0% | 1.47x | 0.000% / 0.018% |
| 2025-09-07 11:45 | 7.77x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.036% / 0.006% / 0.042% | True breakout | 16.7% | 50.0% | 33.3% | 2.05x | 0.060% / 0.000% |
| 2025-09-07 13:30 | 6.16x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.006% / 0.060% / 0.000% | True breakout | 57.1% | 42.9% | 0.0% | 2.84x | 0.072% / 0.012% |
| 2025-09-07 16:15 | 3.28x | Small-body bearish | Flat / fading | -0.006% / -0.006% / -0.012% | Weak move without breakout | 56.3% | 18.8% | 25.0% | 2.73x | 0.030% / 0.012% |
| 2025-09-08 07:00 | 21.71x | Bearish pin-bar / upper rejection | Flat / fading | 0.060% / 0.090% / 0.084% | Position building in range | 40.4% | 50.9% | 8.8% | 11.40x | 0.096% / 0.036% |
| 2025-09-08 07:15 | 3.94x | Full-bodied bullish | Impulse / continuation | 0.030% / -0.042% / 0.096% | True breakout | 61.1% | 22.2% | 16.7% | 2.03x | 0.138% / 0.096% |
| 2025-09-08 07:45 | 4.07x | Bullish pin-bar / lower rejection | Reversal | 0.066% / 0.138% / 0.150% | Liquidity sweep / reversal | 40.9% | 18.2% | 40.9% | 2.35x | 0.012% / 0.287% |
| 2025-09-08 08:15 | 4.69x | Small-body bullish | Impulse / continuation | 0.119% / 0.012% / 0.155% | True breakout | 47.8% | 30.4% | 21.7% | 2.05x | 0.215% / 0.030% |
| 2025-09-08 08:30 | 4.18x | Full-bodied bullish | Flat / fading | -0.107% / 0.066% / -0.012% | Weak move without breakout | 80.8% | 19.2% | 0.0% | 2.04x | 0.095% / 0.149% |
| 2025-09-08 09:00 | 4.56x | Full-bodied bullish | Flat / fading | -0.030% / -0.078% / -0.119% | Weak move without breakout | 85.3% | 14.7% | 0.0% | 2.12x | 0.018% / 0.197% |
| 2025-09-08 09:15 | 2.94x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.048% / -0.131% / -0.173% | True breakout | 16.7% | 50.0% | 33.3% | 0.66x | 0.197% / 0.036% |
| 2025-09-08 11:45 | 2.01x | Bullish pin-bar / lower rejection | Reversal | 0.012% / 0.036% / 0.072% | Liquidity sweep / reversal | 28.0% | 28.0% | 44.0% | 1.11x | 0.048% / 0.072% |
| 2025-09-08 15:15 | 3.03x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.077% / 0.018% | True breakout | 70.5% | 0.0% | 29.5% | 3.18x | 0.113% / 0.054% |
| 2025-09-08 15:30 | 2.99x | Bearish pin-bar / upper rejection | Reversal | 0.077% / 0.036% / -0.036% | Liquidity sweep / reversal | 16.0% | 76.0% | 8.0% | 1.64x | 0.095% / 0.113% |
| 2025-09-08 15:45 | 2.56x | Bullish pin-bar / lower rejection | Reversal | -0.042% / -0.059% / -0.184% | Liquidity sweep / reversal | 44.0% | 12.0% | 44.0% | 1.58x | 0.012% / 0.250% |
| 2025-09-09 07:00 | 4.54x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.083% / 0.083% / 0.083% | True breakout | 37.9% | 13.8% | 48.3% | 2.88x | 0.113% / 0.036% |
| 2025-09-09 10:00 | 5.09x | Doji | Flat / fading | -0.036% / -0.030% / -0.036% | Weak move without breakout | 0.0% | 42.9% | 57.1% | 1.62x | 0.107% / 0.107% |
| 2025-09-09 10:15 | 2.65x | Bullish pin-bar / lower rejection | Reversal | 0.006% / 0.000% / 0.077% | Liquidity sweep / reversal | 31.6% | 5.3% | 63.2% | 1.44x | 0.071% / 0.089% |
| 2025-09-09 10:45 | 3.00x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.077% / 0.071% | Liquidity sweep / reversal | 4.3% | 43.5% | 52.2% | 1.70x | 0.018% / 0.178% |
| 2025-09-09 12:30 | 7.09x | Full-bodied bearish | Impulse / continuation | -0.054% / 0.048% / -0.083% | True breakout | 89.3% | 3.6% | 7.1% | 4.90x | 0.226% / 0.071% |
| 2025-09-09 12:45 | 2.82x | Bullish pin-bar / lower rejection | Reversal | 0.101% / -0.083% / -0.089% | Liquidity sweep / reversal | 19.4% | 36.1% | 44.4% | 1.63x | 0.196% / 0.125% |
| 2025-09-10 07:00 | 2.73x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.089% / -0.131% / -0.185% | True breakout | 30.0% | 63.3% | 6.7% | 2.80x | 0.232% / 0.000% |
| 2025-09-10 09:00 | 11.90x | Bearish pin-bar / upper rejection | Reversal | 0.012% / 0.012% / 0.006% | Liquidity sweep / reversal | 1.0% | 93.9% | 5.1% | 6.83x | 0.125% / 0.143% |
| 2025-09-10 09:15 | 2.61x | Bullish pin-bar / lower rejection | Reversal | 0.000% / -0.060% / 0.024% | Liquidity sweep / reversal | 3.6% | 7.1% | 89.3% | 1.32x | 0.113% / 0.101% |
| 2025-09-10 10:00 | 5.86x | Bearish pin-bar / upper rejection | Flat / fading | 0.030% / 0.048% / 0.018% | Weak move without breakout | 25.0% | 50.0% | 25.0% | 1.31x | 0.107% / 0.060% |
| 2025-09-10 12:15 | 2.77x | Small-body bearish | Flat / fading | 0.060% / 0.126% / 0.078% | Weak move without breakout | 59.5% | 4.8% | 35.7% | 1.62x | 0.048% / 0.168% |
| 2025-09-11 07:45 | 4.83x | Full-bodied bullish | Impulse / continuation | 0.060% / 0.114% / 0.066% | True breakout | 64.3% | 32.1% | 3.6% | 1.90x | 0.156% / 0.006% |
| 2025-09-11 10:00 | 2.54x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.120% / -0.114% / -0.468% | True breakout | 37.5% | 50.0% | 12.5% | 0.94x | 0.582% / 0.042% |
| 2025-09-11 10:15 | 4.19x | Full-bodied bearish | Impulse / continuation | 0.006% / -0.361% / -0.607% | True breakout | 69.0% | 24.1% | 6.9% | 1.66x | 0.649% / 0.054% |
| 2025-09-11 10:30 | 3.80x | Bullish pin-bar / lower rejection | Reversal | -0.367% / -0.355% / -0.685% | Liquidity sweep / reversal | 5.4% | 21.6% | 73.0% | 2.14x | -0.006% / 0.847% |
| 2025-09-11 10:45 | 5.15x | Full-bodied bearish | Impulse / continuation | 0.012% / -0.247% / -0.326% | True breakout | 93.7% | 0.0% | 6.3% | 3.61x | 0.483% / 0.103% |
| 2025-09-11 11:00 | 3.75x | Bullish pin-bar / lower rejection | Reversal | -0.259% / -0.332% / -0.332% | Liquidity sweep / reversal | 5.9% | 44.1% | 50.0% | 1.56x | 0.000% / 0.495% |
| 2025-09-11 11:15 | 2.91x | Full-bodied bearish | Impulse / continuation | -0.073% / -0.079% / -0.018% | True breakout | 80.0% | 6.0% | 14.0% | 2.10x | 0.236% / 0.024% |
| 2025-09-11 11:30 | 5.48x | Bullish pin-bar / lower rejection | Reversal | -0.006% / 0.000% / 0.188% | Liquidity sweep / reversal | 30.8% | 0.0% | 69.2% | 1.54x | 0.109% / 0.200% |
| 2025-09-11 15:30 | 4.18x | Bullish pin-bar / lower rejection | Flat / fading | -0.140% / -0.549% / -0.238% | Weak move without breakout | 47.6% | 0.0% | 52.4% | 7.19x | 0.567% / 0.012% |
| 2025-09-11 16:00 | 2.48x | Full-bodied bearish | Reversal | 0.331% / 0.313% / 0.564% | Liquidity sweep / reversal | 94.4% | 1.4% | 4.2% | 1.92x | 0.012% / 0.999% |
| 2025-09-11 16:45 | 3.37x | Bearish pin-bar / upper rejection | Reversal | 0.189% / -0.195% / 0.018% | Liquidity sweep / reversal | 6.9% | 64.2% | 28.9% | 3.67x | 0.257% / 0.257% |
| 2025-09-12 10:00 | 14.80x | Full-bodied bearish | Impulse / continuation | 0.043% / 0.184% / -0.049% | True breakout | 83.3% | 0.0% | 16.7% | 7.12x | 0.282% / 0.203% |
| 2025-09-12 10:15 | 4.70x | Bearish pin-bar / upper rejection | Reversal | 0.141% / -0.252% / -0.166% | Liquidity sweep / reversal | 20.5% | 52.3% | 27.3% | 1.81x | 0.160% / 0.325% |
| 2025-09-12 10:45 | 4.23x | Full-bodied bearish | Reversal | 0.160% / 0.086% / 0.326% | Liquidity sweep / reversal | 82.7% | 1.3% | 16.0% | 2.76x | 0.018% / 0.412% |
| 2025-09-12 13:30 | 14.44x | Bullish pin-bar / lower rejection | Flat / fading | -0.037% / 0.141% / -0.074% | Position building in range | 23.9% | 0.0% | 76.1% | 4.08x | 0.264% / 0.258% |
| 2025-09-12 15:30 | 2.92x | Full-bodied bearish | Impulse / continuation | 0.006% / -0.137% / -0.708% | True breakout | 83.7% | 6.5% | 9.8% | 1.88x | 0.788% / 0.410% |
| 2025-09-12 16:30 | 2.74x | Full-bodied bearish | Flat / fading | -0.119% / 0.044% / 0.144% | Weak move without breakout | 80.0% | 7.6% | 12.4% | 1.65x | 0.431% / 0.231% |
| 2025-09-13 17:00 | 4.55x | Full-bodied bearish | Impulse / continuation | -0.031% / -0.119% / -0.044% | True breakout | 63.6% | 18.2% | 18.2% | 2.48x | 0.157% / 0.000% |
| 2025-09-13 17:15 | 3.04x | Small-body bearish | Impulse / continuation | -0.088% / -0.038% / 0.006% | True breakout | 57.1% | 14.3% | 28.6% | 1.40x | 0.126% / 0.013% |
| 2025-09-13 17:30 | 3.21x | Full-bodied bearish | Flat / fading | 0.050% / 0.075% / 0.031% | Weak move without breakout | 80.0% | 0.0% | 20.0% | 4.06x | 0.038% / 0.094% |
| 2025-09-14 12:00 | 3.66x | Full-bodied bullish | Impulse / continuation | 0.057% / 0.050% / 0.164% | True breakout | 85.7% | 14.3% | 0.0% | 0.72x | 0.176% / 0.038% |
| 2025-09-14 15:00 | 3.77x | Small-body bullish | Flat / fading | 0.019% / 0.019% / 0.050% | Weak move without breakout | 56.5% | 39.1% | 4.3% | 2.00x | 0.063% / 0.069% |
| 2025-09-14 15:30 | 2.46x | Doji / lower rejection | Flat / fading | -0.056% / 0.031% / 0.006% | Weak move without breakout | 0.0% | 30.0% | 70.0% | 1.58x | 0.075% / 0.075% |
| 2025-09-15 07:00 | 7.41x | Bearish pin-bar / upper rejection | Flat / fading | 0.056% / -0.081% / 0.038% | Weak move without breakout | 34.4% | 59.4% | 6.3% | 2.22x | 0.094% / 0.119% |
| 2025-09-15 07:15 | 2.94x | Bearish pin-bar / upper rejection | Reversal | -0.138% / -0.025% / -0.050% | Liquidity sweep / reversal | 40.9% | 45.5% | 13.6% | 1.41x | 0.038% / 0.150% |
| 2025-09-15 07:30 | 3.01x | Full-bodied bearish | Flat / fading | 0.113% / 0.119% / 0.094% | Position building in range | 80.0% | 13.3% | 6.7% | 1.86x | 0.006% / 0.169% |
| 2025-09-15 09:00 | 5.46x | Small-body bearish | Flat / fading | 0.044% / -0.013% / 0.182% | Position building in range | 59.2% | 14.3% | 26.5% | 2.69x | 0.069% / 0.220% |
| 2025-09-15 09:15 | 3.36x | Small-body bullish | Flat / fading | -0.056% / -0.013% / -0.038% | Weak move without breakout | 38.5% | 30.8% | 30.8% | 1.23x | 0.176% / 0.107% |
| 2025-09-15 10:00 | 2.88x | Full-bodied bullish | Reversal | -0.176% / -0.364% / -0.658% | Liquidity sweep / reversal | 72.7% | 18.2% | 9.1% | 1.41x | 0.025% / 0.834% |
| 2025-09-15 10:15 | 4.92x | Full-bodied bearish | Impulse / continuation | -0.188% / -0.502% / -0.685% | True breakout | 73.7% | 10.5% | 15.8% | 1.54x | 0.904% / 0.088% |
| 2025-09-15 10:30 | 3.69x | Small-body bearish | Impulse / continuation | -0.315% / -0.296% / -0.510% | True breakout | 51.7% | 24.1% | 24.1% | 2.29x | 0.717% / 0.044% |
| 2025-09-15 10:45 | 3.55x | Full-bodied bearish | Impulse / continuation | 0.019% / -0.183% / -0.183% | True breakout | 81.7% | 13.3% | 5.0% | 2.21x | 0.404% / 0.095% |
| 2025-09-15 11:15 | 4.08x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / 0.000% / -0.044% | Position building in range | 41.9% | 10.8% | 47.3% | 2.42x | 0.190% / 0.152% |
| 2025-09-15 11:30 | 3.05x | Bullish pin-bar / lower rejection | Reversal | 0.013% / 0.032% / -0.082% | Liquidity sweep / reversal | 3.7% | 44.4% | 51.9% | 1.59x | 0.120% / 0.152% |
| 2025-09-16 07:00 | 2.69x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.095% / 0.095% / 0.082% | True breakout | 17.6% | 41.2% | 41.2% | 1.38x | 0.133% / 0.013% |
| 2025-09-16 08:15 | 8.69x | Full-bodied bullish | Impulse / continuation | 0.063% / -0.025% / -0.132% | True breakout | 86.2% | 13.8% | 0.0% | 5.34x | 0.151% / 0.283% |
| 2025-09-16 08:30 | 3.84x | Bearish pin-bar / upper rejection | Reversal | -0.088% / -0.271% / -0.101% | Liquidity sweep / reversal | 33.3% | 42.4% | 24.2% | 2.32x | 0.031% / 0.346% |
| 2025-09-16 09:00 | 4.48x | Full-bodied bearish | Impulse / continuation | 0.076% / 0.170% / 0.032% | True breakout | 61.4% | 11.4% | 27.3% | 2.71x | 0.196% / 0.189% |
| 2025-09-16 10:00 | 2.80x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.095% / 0.195% / 0.126% | True breakout | 28.9% | 5.3% | 65.8% | 1.61x | 0.290% / 0.025% |
| 2025-09-16 11:30 | 4.25x | Full-bodied bearish | Impulse / continuation | -0.057% / -0.335% / -0.608% | True breakout | 75.9% | 3.4% | 20.7% | 2.79x | 0.620% / 0.063% |
| 2025-09-16 12:00 | 2.77x | Small-body bearish | Impulse / continuation | 0.038% / -0.273% / -0.330% | True breakout | 53.0% | 12.0% | 34.9% | 2.33x | 0.514% / 0.152% |
| 2025-09-16 13:00 | 2.18x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / 0.140% / 0.159% | Weak move without breakout | 2.8% | 19.4% | 77.8% | 0.90x | 0.236% / 0.089% |
| 2025-09-16 16:45 | 2.93x | Small-body bullish | Impulse / continuation | 0.482% / 0.152% / 0.247% | True breakout | 59.8% | 39.1% | 1.1% | 2.93x | 0.558% / 0.006% |
| 2025-09-16 17:00 | 2.55x | Full-bodied bullish | Flat / fading | -0.328% / -0.227% / -0.391% | Position building in range | 84.3% | 13.5% | 2.2% | 2.49x | 0.032% / 0.423% |
| 2025-09-17 07:00 | 3.53x | Small-body bullish | Flat / fading | -0.063% / -0.063% / -0.051% | Position building in range | 48.3% | 20.7% | 31.0% | 2.52x | 0.000% / 0.101% |
| 2025-09-17 09:00 | 3.50x | Small-body bearish | Impulse / continuation | -0.234% / -0.253% / -0.285% | True breakout | 52.9% | 29.4% | 17.6% | 1.43x | 0.469% / 0.006% |
| 2025-09-17 09:15 | 5.92x | Full-bodied bearish | Impulse / continuation | -0.019% / -0.108% / 0.013% | True breakout | 80.9% | 0.0% | 19.1% | 3.96x | 0.235% / 0.114% |
| 2025-09-17 09:30 | 3.19x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.089% / -0.032% / -0.006% | False breakout | 4.8% | 95.2% | 0.0% | 1.45x | 0.216% / 0.089% |
| 2025-09-17 10:00 | 4.03x | Bullish pin-bar / lower rejection | Flat / fading | 0.064% / 0.025% / 0.032% | Weak move without breakout | 21.4% | 31.0% | 47.6% | 2.51x | 0.133% / 0.083% |
| 2025-09-17 12:45 | 2.67x | Full-bodied bearish | Reversal | 0.032% / 0.248% / 0.440% | Liquidity sweep / reversal | 69.6% | 0.0% | 30.4% | 1.77x | 0.057% / 0.586% |
| 2025-09-17 13:15 | 2.25x | Full-bodied bullish | Impulse / continuation | 0.172% / 0.191% / 0.102% | True breakout | 85.7% | 4.8% | 9.5% | 1.62x | 0.337% / 0.044% |
| 2025-09-17 13:45 | 3.11x | Bearish pin-bar / upper rejection | Reversal | -0.025% / -0.089% / -0.095% | Liquidity sweep / reversal | 10.7% | 82.1% | 7.1% | 1.07x | 0.089% / 0.235% |
| 2025-09-17 15:30 | 2.02x | Bullish pin-bar / lower rejection | Flat / fading | 0.045% / 0.032% / 0.025% | Weak move without breakout | 26.9% | 7.7% | 65.4% | 0.94x | 0.057% / 0.255% |
| 2025-09-17 17:15 | 4.50x | Full-bodied bullish | Impulse / continuation | 0.221% / 0.354% / 0.335% | True breakout | 67.9% | 17.0% | 15.2% | 3.74x | 0.436% / 0.076% |
| 2025-09-17 17:30 | 2.82x | Full-bodied bullish | Flat / fading | 0.132% / -0.063% / 0.101% | Weak move without breakout | 69.1% | 14.5% | 16.4% | 1.53x | 0.214% / 0.126% |
| 2025-09-17 17:45 | 2.28x | Full-bodied bullish | Reversal | -0.195% / -0.019% / -0.126% | Liquidity sweep / reversal | 70.0% | 26.7% | 3.3% | 0.80x | 0.082% / 0.258% |
| 2025-09-18 10:00 | 5.81x | Small-body bearish | Reversal | 0.196% / 0.120% / 0.013% | Liquidity sweep / reversal | 38.2% | 23.5% | 38.2% | 1.55x | 0.114% / 0.304% |
| 2025-09-18 10:15 | 3.14x | Full-bodied bullish | Reversal | -0.076% / -0.221% / -0.139% | Liquidity sweep / reversal | 60.4% | 35.4% | 4.2% | 2.07x | 0.057% / 0.360% |
| 2025-09-18 10:45 | 2.83x | Full-bodied bearish | Flat / fading | 0.038% / 0.082% / 0.032% | Weak move without breakout | 76.7% | 0.0% | 23.3% | 1.18x | 0.139% / 0.146% |
| 2025-09-18 13:00 | 2.55x | Bearish pin-bar / upper rejection | Reversal | 0.127% / -0.102% / -0.121% | Liquidity sweep / reversal | 29.3% | 58.5% | 12.2% | 1.43x | 0.210% / 0.152% |
| 2025-09-18 15:00 | 3.06x | Full-bodied bearish | Reversal | 0.287% / 0.153% / 0.159% | Liquidity sweep / reversal | 74.4% | 0.0% | 25.6% | 1.40x | 0.032% / 0.363% |
| 2025-09-18 15:15 | 3.56x | Full-bodied bullish | Flat / fading | -0.133% / -0.114% / -0.210% | Weak move without breakout | 75.8% | 19.4% | 4.8% | 2.13x | 0.013% / 0.445% |
| 2025-09-18 15:30 | 2.06x | Full-bodied bearish | Impulse / continuation | 0.019% / 0.006% / -0.013% | True breakout | 61.8% | 0.0% | 38.2% | 1.06x | 0.312% / 0.146% |
| 2025-09-18 20:45 | 3.93x | Full-bodied bearish | Flat / fading | 0.205% / 0.320% / 0.326% | Position building in range | 80.9% | 0.0% | 19.1% | 4.61x | 0.032% / 0.377% |
| 2025-09-19 10:00 | 4.83x | Bearish pin-bar / upper rejection | Reversal | 0.287% / 0.146% / -0.051% | Liquidity sweep / reversal | 15.2% | 62.1% | 22.7% | 2.62x | 0.134% / 0.338% |
| 2025-09-19 10:15 | 2.92x | Full-bodied bullish | Reversal | -0.140% / -0.191% / -0.324% | Liquidity sweep / reversal | 70.1% | 11.9% | 17.9% | 2.29x | 0.044% / 0.527% |
| 2025-09-19 11:00 | 2.63x | Full-bodied bearish | Flat / fading | 0.013% / -0.134% / -0.070% | Weak move without breakout | 63.9% | 0.0% | 36.1% | 1.14x | 0.204% / 0.038% |
| 2025-09-19 11:15 | 2.95x | Bullish pin-bar / lower rejection | Reversal | -0.147% / -0.140% / -0.140% | Liquidity sweep / reversal | 6.3% | 0.0% | 93.7% | 0.97x | 0.025% / 0.331% |
| 2025-09-19 12:15 | 3.30x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / 0.000% / -0.108% | Position building in range | 20.4% | 18.4% | 61.2% | 1.31x | 0.159% / 0.077% |
| 2025-09-19 13:30 | 2.62x | Full-bodied bearish | Flat / fading | 0.102% / 0.198% / 0.006% | Weak move without breakout | 75.6% | 11.1% | 13.3% | 1.27x | 0.038% / 0.262% |
| 2025-09-19 14:45 | 3.55x | Bullish pin-bar / lower rejection | Flat / fading | -0.249% / -0.083% / -0.045% | Weak move without breakout | 48.2% | 4.4% | 47.4% | 3.57x | 0.045% / 0.268% |
| 2025-09-19 17:45 | 4.18x | Full-bodied bearish | Impulse / continuation | -0.161% / -0.109% / -0.399% | True breakout | 66.7% | 22.2% | 11.1% | 2.30x | 0.560% / 0.103% |
| 2025-09-22 10:00 | 2.77x | Full-bodied bullish | Flat / fading | -0.123% / -0.305% / -0.149% | Weak move without breakout | 70.2% | 9.5% | 20.2% | 2.54x | 0.149% / 0.331% |
| 2025-09-22 10:15 | 4.01x | Bullish pin-bar / lower rejection | Reversal | -0.182% / 0.176% / 0.046% | Liquidity sweep / reversal | 50.0% | 5.3% | 44.7% | 1.04x | 0.208% / 0.273% |
| 2025-09-22 10:30 | 3.69x | Full-bodied bearish | Reversal | 0.358% / 0.156% / 0.163% | Liquidity sweep / reversal | 80.0% | 8.6% | 11.4% | 0.90x | -0.020% / 0.456% |
| 2025-09-22 10:45 | 3.33x | Full-bodied bullish | Flat / fading | -0.201% / -0.130% / -0.136% | Position building in range | 77.6% | 22.4% | 0.0% | 1.87x | 0.071% / 0.299% |
| 2025-09-22 11:00 | 2.92x | Full-bodied bearish | Impulse / continuation | 0.072% / 0.007% / -0.163% | True breakout | 65.9% | 29.5% | 4.5% | 1.16x | 0.299% / 0.228% |
| 2025-09-22 14:45 | 4.22x | Small-body bullish | Flat / fading | -0.251% / -0.290% / -0.316% | Position building in range | 53.1% | 33.2% | 13.8% | 3.99x | 0.161% / 0.393% |
| 2025-09-23 07:00 | 3.74x | Full-bodied bullish | Flat / fading | -0.038% / -0.077% / 0.058% | Weak move without breakout | 85.1% | 12.8% | 2.1% | 3.18x | 0.122% / 0.090% |
| 2025-09-23 09:30 | 3.82x | Bearish pin-bar / upper rejection | Flat / fading | -0.006% / -0.013% / -0.051% | Weak move without breakout | 49.0% | 45.1% | 5.9% | 2.82x | 0.179% / 0.192% |
| 2025-09-23 09:45 | 3.16x | Bearish pin-bar / upper rejection | Reversal | -0.006% / 0.000% / -0.211% | Liquidity sweep / reversal | 4.8% | 69.0% | 26.2% | 2.02x | 0.135% / 0.327% |
| 2025-09-23 10:00 | 3.22x | Bullish pin-bar / lower rejection | Reversal | 0.006% / -0.038% / -0.416% | Liquidity sweep / reversal | 2.9% | 17.6% | 79.4% | 1.45x | 0.141% / 0.474% |
| 2025-09-23 10:30 | 3.06x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.167% / -0.378% / -0.154% | True breakout | 8.6% | 71.4% | 20.0% | 1.30x | 0.590% / 0.006% |
| 2025-09-23 10:45 | 3.51x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.212% / -0.225% / 0.180% | False breakout | 57.8% | 2.2% | 40.0% | 1.73x | 0.424% / 0.250% |
| 2025-09-23 11:00 | 3.17x | Full-bodied bearish | Reversal | -0.013% / 0.225% / 0.483% | Liquidity sweep / reversal | 78.0% | 0.0% | 22.0% | 1.47x | 0.212% / 0.534% |
| 2025-09-23 15:00 | 1.82x | Bearish pin-bar / upper rejection | Flat / fading | -0.152% / -0.108% / 0.228% | Weak move without breakout | 53.2% | 46.8% | 0.0% | 1.26x | 0.323% / 0.234% |
| 2025-09-23 22:00 | 7.28x | Full-bodied bearish | Flat / fading | 0.123% / -0.084% / -0.240% | Weak move without breakout | 86.2% | 0.0% | 13.8% | 5.81x | 0.467% / 0.331% |
| 2025-09-24 10:00 | 3.19x | Bullish pin-bar / lower rejection | Flat / fading | -0.200% / -0.032% / 0.000% | Weak move without breakout | 55.2% | 0.8% | 44.0% | 2.99x | 0.122% / 0.284% |
| 2025-09-24 10:15 | 2.62x | Small-body bearish | Reversal | 0.168% / 0.213% / 0.852% | Liquidity sweep / reversal | 49.2% | 32.8% | 18.0% | 1.24x | 0.084% / 0.910% |
| 2025-09-25 09:00 | 3.83x | Bullish pin-bar / lower rejection | Reversal | 0.197% / 0.191% / 0.102% | Liquidity sweep / reversal | 51.7% | 6.7% | 41.7% | 2.85x | 0.108% / 0.344% |
| 2025-09-25 10:00 | 3.07x | Full-bodied bearish | Impulse / continuation | -0.331% / -0.235% / -0.369% | True breakout | 63.6% | 0.0% | 36.4% | 2.01x | 0.489% / 0.025% |
| 2025-09-25 10:15 | 2.69x | Full-bodied bearish | Flat / fading | 0.096% / 0.013% / 0.026% | Weak move without breakout | 85.7% | 3.2% | 11.1% | 2.24x | 0.159% / 0.191% |
| 2025-09-25 10:30 | 3.45x | Bullish pin-bar / lower rejection | Reversal | -0.083% / -0.134% / 0.032% | Liquidity sweep / reversal | 32.6% | 18.6% | 48.8% | 1.33x | 0.096% / 0.255% |
| 2025-09-25 18:15 | 5.09x | Full-bodied bearish | Impulse / continuation | 0.141% / 0.212% / -0.122% | True breakout | 92.9% | 0.0% | 7.1% | 3.11x | 0.340% / 0.347% |
| 2025-09-25 19:15 | 2.74x | Small-body bearish | Flat / fading | -0.051% / 0.116% / -0.071% | Weak move without breakout | 37.4% | 30.8% | 31.8% | 3.21x | 0.360% / 0.161% |
| 2025-09-26 07:00 | 2.86x | Full-bodied bullish | Reversal | -0.275% / -0.525% / -0.436% | Liquidity sweep / reversal | 60.9% | 1.6% | 37.5% | 3.42x | -0.019% / 0.538% |
| 2025-09-26 07:45 | 2.55x | Bearish pin-bar / upper rejection | Reversal | 0.097% / 0.322% / 0.148% | Liquidity sweep / reversal | 6.2% | 90.6% | 3.1% | 1.29x | -0.013% / 0.406% |
| 2025-09-26 09:00 | 3.12x | Full-bodied bullish | Flat / fading | -0.090% / -0.103% / -0.186% | Weak move without breakout | 95.7% | 4.3% | 0.0% | 1.56x | 0.186% / 0.218% |
| 2025-09-26 09:45 | 2.97x | Bearish pin-bar / upper rejection | Reversal | -0.083% / -0.334% / -0.334% | Liquidity sweep / reversal | 3.2% | 77.4% | 19.4% | 0.91x | 0.289% / 0.488% |
| 2025-09-26 10:00 | 4.98x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.250% / -0.295% / -0.141% | True breakout | 25.4% | 66.7% | 7.9% | 1.82x | 0.405% / 0.064% |
| 2025-09-26 10:15 | 4.19x | Small-body bearish | Flat / fading | -0.045% / 0.000% / 0.013% | Weak move without breakout | 54.3% | 15.7% | 30.0% | 1.85x | 0.155% / 0.258% |
| 2025-09-26 10:45 | 3.08x | Bearish pin-bar / upper rejection | Flat / fading | 0.109% / 0.013% / 0.026% | Weak move without breakout | 18.6% | 44.2% | 37.2% | 1.11x | 0.258% / 0.058% |
| 2025-09-26 17:45 | 2.53x | Full-bodied bullish | Flat / fading | -0.115% / -0.102% / 0.064% | Weak move without breakout | 82.2% | 13.7% | 4.1% | 2.22x | 0.128% / 0.147% |
| 2025-09-26 18:15 | 2.64x | Bearish pin-bar / upper rejection | Flat / fading | 0.134% / 0.166% / 0.250% | Weak move without breakout | 4.7% | 83.7% | 11.6% | 1.19x | 0.327% / 0.045% |
| 2025-09-28 10:00 | 4.08x | Bearish pin-bar / upper rejection | Flat / fading | 0.013% / -0.006% / -0.013% | Position building in range | 37.5% | 62.5% | 0.0% | 4.00x | 0.013% / 0.026% |
| 2025-09-28 12:00 | 2.57x | Full-bodied bearish | Reversal | 0.000% / 0.006% / 0.026% | Liquidity sweep / reversal | 75.0% | 0.0% | 25.0% | 0.93x | 0.013% / 0.039% |
| 2025-09-28 12:15 | 3.59x | Doji / upper rejection | Flat / fading | 0.006% / 0.019% / 0.026% | Weak move without breakout | 0.0% | 66.7% | 33.3% | 1.38x | 0.045% / 0.045% |
| 2025-09-28 17:45 | 3.65x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.071% / -0.051% / -0.071% | True breakout | 42.9% | 0.0% | 57.1% | 1.53x | 0.096% / 0.000% |
| 2025-09-28 18:00 | 3.00x | Full-bodied bearish | Reversal | 0.019% / 0.006% / 0.122% | Liquidity sweep / reversal | 64.3% | 14.3% | 21.4% | 2.88x | 0.026% / 0.122% |
| 2025-09-28 18:30 | 2.90x | Bullish pin-bar / lower rejection | Reversal | -0.006% / 0.116% / 0.180% | Liquidity sweep / reversal | 25.0% | 12.5% | 62.5% | 1.40x | 0.032% / 0.296% |
| 2025-09-29 07:00 | 18.65x | Bullish pin-bar / lower rejection | Reversal | -0.064% / -0.115% / 0.026% | Liquidity sweep / reversal | 29.7% | 21.6% | 48.6% | 5.57x | 0.058% / 0.160% |
| 2025-09-29 07:15 | 3.10x | Bullish pin-bar / lower rejection | Reversal | -0.051% / 0.064% / 0.083% | Liquidity sweep / reversal | 47.1% | 11.8% | 41.2% | 1.89x | 0.096% / 0.135% |
| 2025-09-29 07:30 | 3.71x | Small-body bearish | Reversal | 0.116% / 0.141% / 0.135% | Liquidity sweep / reversal | 32.0% | 40.0% | 28.0% | 2.50x | 0.000% / 0.186% |
| 2025-09-29 07:45 | 3.30x | Full-bodied bullish | Flat / fading | 0.026% / 0.019% / -0.026% | Weak move without breakout | 66.7% | 33.3% | 0.0% | 2.32x | 0.071% / 0.058% |
| 2025-09-29 09:00 | 6.46x | Bullish pin-bar / lower rejection | Reversal | 0.071% / 0.058% / 0.301% | Liquidity sweep / reversal | 10.3% | 41.4% | 48.3% | 1.85x | 0.135% / 0.366% |
| 2025-09-29 09:30 | 2.72x | Bearish pin-bar / upper rejection | Reversal | -0.006% / 0.244% / 0.474% | Liquidity sweep / reversal | 10.0% | 70.0% | 20.0% | 1.16x | 0.192% / 0.538% |
| 2025-09-29 10:00 | 9.05x | Small-body bullish | Impulse / continuation | -0.013% / 0.230% / 0.326% | True breakout | 53.8% | 12.8% | 33.3% | 4.11x | 0.384% / 0.160% |
| 2025-09-29 10:15 | 4.06x | Bullish pin-bar / lower rejection | Reversal | 0.243% / 0.288% / 0.537% | Liquidity sweep / reversal | 6.7% | 42.2% | 51.1% | 1.86x | 0.000% / 0.588% |
| 2025-09-29 10:30 | 5.21x | Full-bodied bullish | Impulse / continuation | 0.045% / 0.096% / 0.204% | True breakout | 79.2% | 20.8% | 0.0% | 1.84x | 0.434% / 0.070% |
| 2025-09-29 11:00 | 3.11x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.198% / 0.108% / 0.274% | True breakout | 40.0% | 45.0% | 15.0% | 0.74x | 0.338% / 0.102% |
| 2025-09-29 18:00 | 4.02x | Full-bodied bearish | Impulse / continuation | -0.386% / -0.515% / -0.560% | True breakout | 66.7% | 0.0% | 33.3% | 2.22x | 0.759% / 0.006% |
| 2025-09-29 18:15 | 4.59x | Bullish pin-bar / lower rejection | Flat / fading | -0.129% / -0.142% / -0.097% | Weak move without breakout | 54.5% | 0.0% | 45.5% | 3.37x | 0.375% / 0.019% |
| 2025-09-29 18:30 | 2.51x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / -0.045% / 0.045% | Position building in range | 32.8% | 4.9% | 62.3% | 1.52x | 0.142% / 0.123% |
| 2025-09-30 10:00 | 14.29x | Full-bodied bearish | Impulse / continuation | -0.266% / -0.136% / -0.019% | True breakout | 70.4% | 1.4% | 28.2% | 4.40x | 0.468% / 0.143% |
| 2025-09-30 10:15 | 5.04x | Small-body bearish | Reversal | 0.130% / 0.300% / 0.202% | Liquidity sweep / reversal | 52.6% | 30.3% | 17.1% | 3.72x | 0.202% / 0.358% |
| 2025-09-30 10:30 | 3.00x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.169% / 0.117% / -0.429% | False breakout | 33.9% | 13.6% | 52.5% | 2.31x | 0.228% / 0.566% |
| 2025-09-30 11:30 | 2.95x | Full-bodied bearish | Impulse / continuation | 0.163% / -0.209% / -0.993% | True breakout | 78.8% | 0.0% | 21.2% | 2.96x | 1.104% / 0.242% |
| 2025-09-30 12:15 | 3.01x | Full-bodied bearish | Flat / fading | -0.257% / 0.138% / -0.079% | Weak move without breakout | 75.0% | 8.3% | 16.7% | 2.33x | 0.369% / 0.230% |
| 2025-09-30 12:30 | 2.60x | Small-body bearish | Reversal | 0.396% / 0.290% / 0.251% | Liquidity sweep / reversal | 55.9% | 19.1% | 25.0% | 1.27x | 0.020% / 0.488% |
| 2025-10-01 07:45 | 4.27x | Bearish pin-bar / upper rejection | Reversal | 0.019% / -0.026% / -0.065% | Liquidity sweep / reversal | 22.2% | 77.8% | 0.0% | 1.66x | 0.045% / 0.143% |
| 2025-10-01 09:00 | 3.32x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.104% / 0.143% / 0.052% | True breakout | 40.0% | 14.3% | 45.7% | 2.23x | 0.285% / 0.045% |
| 2025-10-01 09:15 | 9.15x | Bearish pin-bar / upper rejection | Flat / fading | 0.039% / 0.019% / -0.045% | Weak move without breakout | 24.0% | 56.0% | 20.0% | 2.86x | 0.071% / 0.155% |
| 2025-10-01 10:00 | 5.29x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.006% / -0.039% / -0.253% | True breakout | 37.9% | 10.3% | 51.7% | 1.40x | 0.544% / 0.084% |
| 2025-10-01 10:45 | 4.77x | Full-bodied bearish | Impulse / continuation | 0.241% / 0.228% / 0.104% | True breakout | 89.7% | 0.0% | 10.3% | 3.57x | 0.228% / 0.339% |
| 2025-10-01 15:00 | 4.72x | Bullish pin-bar / lower rejection | Flat / fading | -0.288% / 0.098% / 0.255% | Weak move without breakout | 59.0% | 0.0% | 41.0% | 2.28x | 0.294% / 0.294% |
| 2025-10-01 17:15 | 2.77x | Small-body bearish | Flat / fading | -0.020% / 0.230% / 0.210% | Weak move without breakout | 44.8% | 27.6% | 27.6% | 2.22x | 0.355% / 0.591% |
| 2025-10-01 17:30 | 2.74x | Bullish pin-bar / lower rejection | Reversal | 0.250% / 0.125% / -0.059% | Liquidity sweep / reversal | 7.7% | 13.8% | 78.5% | 1.45x | 0.164% / 0.611% |
| 2025-10-02 07:00 | 2.86x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.020% / -0.138% / -0.361% | True breakout | 25.5% | 40.0% | 34.5% | 2.82x | 0.656% / 0.033% |
| 2025-10-02 07:45 | 4.06x | Bullish pin-bar / lower rejection | Flat / fading | -0.059% / -0.244% / -0.283% | Position building in range | 29.4% | 7.1% | 63.5% | 4.01x | 0.356% / -0.013% |
| 2025-10-02 08:00 | 2.58x | Bullish pin-bar / lower rejection | Flat / fading | -0.184% / -0.217% / -0.138% | Weak move without breakout | 18.9% | 0.0% | 81.1% | 1.40x | 0.296% / 0.040% |
| 2025-10-02 09:45 | 2.88x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.534% / -0.482% / -0.488% | True breakout | 26.7% | 10.0% | 63.3% | 0.90x | 0.640% / 0.106% |
| 2025-10-02 10:00 | 6.66x | Full-bodied bearish | Flat / fading | 0.053% / 0.186% / 0.358% | Weak move without breakout | 71.0% | 19.6% | 9.3% | 3.10x | 0.106% / 0.378% |
| 2025-10-02 10:15 | 4.27x | Bullish pin-bar / lower rejection | Reversal | 0.133% / -0.007% / -0.239% | Liquidity sweep / reversal | 20.5% | 38.5% | 41.0% | 0.95x | 0.331% / 0.305% |
| 2025-10-02 10:30 | 4.44x | Bearish pin-bar / upper rejection | Reversal | -0.139% / 0.172% / -0.516% | Liquidity sweep / reversal | 39.2% | 56.9% | 3.9% | 1.18x | 0.199% / 0.629% |
| 2025-10-02 11:30 | 2.85x | Small-body bearish | Reversal | 0.213% / 0.087% / 0.253% | Liquidity sweep / reversal | 38.3% | 33.3% | 28.3% | 1.29x | 0.020% / 0.346% |
| 2025-10-03 07:30 | 2.66x | Small-body bullish | Impulse / continuation | 0.139% / 0.277% / 0.132% | True breakout | 59.2% | 22.4% | 18.4% | 1.84x | 0.522% / 0.053% |
| 2025-10-03 08:00 | 3.43x | Bearish pin-bar / upper rejection | Reversal | -0.086% / -0.145% / -0.046% | Liquidity sweep / reversal | 32.8% | 57.8% | 9.4% | 2.13x | 0.086% / 0.270% |
| 2025-10-03 10:00 | 9.00x | Full-bodied bullish | Flat / fading | -0.098% / -0.138% / 0.059% | Position building in range | 82.5% | 17.5% | 0.0% | 2.99x | 0.085% / 0.308% |
| 2025-10-03 19:00 | 3.14x | Small-body bearish | Impulse / continuation | -0.459% / -0.779% / -0.573% | True breakout | 56.2% | 21.3% | 22.5% | 2.30x | 0.905% / 0.027% |
| 2025-10-03 19:15 | 4.27x | Full-bodied bearish | Impulse / continuation | -0.321% / -0.127% / -0.341% | True breakout | 81.0% | 6.0% | 13.1% | 1.96x | 0.448% / 0.060% |
| 2025-10-03 19:30 | 3.32x | Full-bodied bearish | Flat / fading | 0.195% / 0.208% / 0.054% | Position building in range | 63.2% | 11.8% | 25.0% | 1.69x | 0.087% / 0.342% |
| 2025-10-06 10:00 | 5.93x | Full-bodied bullish | Impulse / continuation | 0.377% / 0.585% / 0.767% | True breakout | 63.3% | 6.7% | 30.0% | 3.75x | 1.238% / 0.061% |
| 2025-10-06 10:15 | 4.52x | Full-bodied bullish | Impulse / continuation | 0.208% / 0.650% / 0.302% | True breakout | 66.7% | 25.3% | 8.0% | 2.22x | 0.858% / 0.054% |
| 2025-10-06 10:30 | 3.63x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.441% / 0.181% / 0.181% | True breakout | 47.7% | 40.0% | 12.3% | 1.54x | 0.649% / 0.147% |
| 2025-10-06 10:45 | 2.82x | Full-bodied bullish | Flat / fading | -0.260% / -0.346% / -0.246% | Weak move without breakout | 62.4% | 19.3% | 18.3% | 2.38x | 0.206% / 0.493% |
| 2025-10-06 11:00 | 2.78x | Bearish pin-bar / upper rejection | Flat / fading | -0.087% / 0.000% / 0.220% | Weak move without breakout | 50.7% | 47.9% | 1.4% | 1.36x | 0.234% / 0.387% |
| 2025-10-07 07:00 | 2.86x | Small-body bullish | Reversal | -0.139% / -0.139% / -0.040% | Liquidity sweep / reversal | 48.5% | 15.2% | 36.4% | 1.64x | 0.013% / 0.218% |
| 2025-10-07 08:45 | 3.06x | Full-bodied bullish | Reversal | -0.270% / -0.395% / -0.572% | Liquidity sweep / reversal | 87.7% | 4.6% | 7.7% | 3.36x | 0.079% / 0.605% |
| 2025-10-07 09:00 | 3.89x | Full-bodied bearish | Impulse / continuation | -0.125% / -0.198% / -0.336% | True breakout | 73.2% | 21.4% | 5.4% | 2.41x | 0.554% / 0.152% |
| 2025-10-07 10:00 | 4.38x | Bearish pin-bar / upper rejection | Reversal | 0.112% / 0.470% / 0.622% | Liquidity sweep / reversal | 6.2% | 52.5% | 41.3% | 2.63x | 0.126% / 0.761% |
| 2025-10-07 10:15 | 2.79x | Small-body bullish | Impulse / continuation | 0.357% / 0.383% / 1.097% | True breakout | 40.0% | 28.0% | 32.0% | 1.49x | 1.216% / 0.112% |
| 2025-10-07 10:30 | 2.90x | Full-bodied bullish | Impulse / continuation | 0.026% / 0.151% / 0.448% | True breakout | 71.6% | 4.1% | 24.3% | 2.03x | 0.856% / 0.046% |
| 2025-10-07 11:15 | 4.31x | Full-bodied bullish | Flat / fading | -0.288% / -0.157% / -0.523% | Position building in range | 83.6% | 16.4% | 0.0% | 2.69x | 0.046% / 0.556% |
| 2025-10-08 07:00 | 3.90x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / 0.026% / -0.020% | Position building in range | 8.6% | 28.6% | 62.9% | 1.95x | 0.066% / 0.052% |
| 2025-10-08 07:15 | 2.79x | Bearish pin-bar / upper rejection | Reversal | 0.039% / 0.026% / -0.066% | Liquidity sweep / reversal | 20.0% | 60.0% | 20.0% | 0.76x | 0.111% / 0.079% |
| 2025-10-08 09:45 | 3.09x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.026% / -0.190% / -0.204% | True breakout | 47.2% | 11.1% | 41.7% | 2.04x | 0.282% / 0.223% |
| 2025-10-08 10:00 | 7.51x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.164% / -0.177% / -0.237% | True breakout | 7.5% | 64.2% | 28.3% | 2.74x | 0.427% / 0.020% |
| 2025-10-08 10:15 | 6.12x | Full-bodied bearish | Impulse / continuation | -0.013% / -0.013% / -0.105% | True breakout | 64.3% | 2.4% | 33.3% | 1.93x | 0.263% / 0.125% |
| 2025-10-08 10:45 | 2.59x | Doji | Impulse / continuation | -0.059% / -0.092% / -0.165% | True breakout | 0.0% | 40.0% | 60.0% | 0.64x | 0.250% / 0.250% |
| 2025-10-08 11:00 | 3.56x | Bullish pin-bar / lower rejection | Flat / fading | -0.033% / -0.033% / -0.263% | Weak move without breakout | 25.6% | 0.0% | 74.4% | 1.67x | 0.323% / 0.046% |
| 2025-10-08 12:00 | 3.10x | Full-bodied bearish | Impulse / continuation | -0.271% / -0.258% / -0.442% | True breakout | 72.7% | 0.0% | 27.3% | 1.22x | 0.594% / 0.026% |
| 2025-10-08 12:15 | 2.67x | Full-bodied bearish | Impulse / continuation | 0.013% / -0.066% / -0.543% | True breakout | 85.4% | 8.3% | 6.3% | 1.68x | 0.602% / 0.185% |
| 2025-10-08 13:30 | 2.13x | Small-body bearish | Impulse / continuation | -0.347% / -0.600% / -0.533% | True breakout | 51.9% | 19.2% | 28.8% | 1.40x | 0.813% / 0.013% |
| 2025-10-08 13:45 | 2.59x | Full-bodied bearish | Impulse / continuation | -0.254% / -0.288% / -0.816% | True breakout | 81.2% | 3.1% | 15.6% | 1.73x | 0.910% / 0.013% |
| 2025-10-08 14:00 | 3.18x | Full-bodied bearish | Impulse / continuation | -0.034% / 0.067% / -0.349% | True breakout | 66.7% | 3.5% | 29.8% | 1.48x | 0.704% / 0.154% |
| 2025-10-08 14:15 | 2.06x | Bullish pin-bar / lower rejection | Reversal | 0.101% / -0.530% / -0.188% | Liquidity sweep / reversal | 11.9% | 23.8% | 64.3% | 1.04x | 0.671% / 0.188% |
| 2025-10-08 14:45 | 1.92x | Full-bodied bearish | Impulse / continuation | 0.216% / 0.344% / -0.958% | True breakout | 86.2% | 0.9% | 12.8% | 2.60x | 0.998% / 0.378% |
| 2025-10-08 15:45 | 2.10x | Full-bodied bearish | Impulse / continuation | -0.123% / -0.368% / -0.395% | True breakout | 81.0% | 14.0% | 5.0% | 2.07x | 0.497% / 0.198% |
| 2025-10-08 16:00 | 2.80x | Bullish pin-bar / lower rejection | Reversal | -0.246% / 0.150% / -0.266% | Liquidity sweep / reversal | 24.7% | 3.9% | 71.4% | 1.21x | 0.334% / 0.321% |
| 2025-10-08 18:15 | 1.89x | Full-bodied bearish | Reversal | 0.283% / 0.255% / 0.607% | Liquidity sweep / reversal | 74.2% | 10.3% | 15.5% | 1.17x | 0.124% / 0.635% |
| 2025-10-09 09:00 | 7.90x | Full-bodied bearish | Impulse -> reversal | 0.216% / -0.007% / 1.335% | False breakout | 99.4% | 0.0% | 0.6% | 4.39x | 0.389% / 1.627% |
| 2025-10-09 09:15 | 5.82x | Bullish pin-bar / lower rejection | Reversal | -0.222% / 0.472% / 1.193% | Liquidity sweep / reversal | 29.4% | 14.7% | 55.9% | 2.08x | 1.409% / 0.291% |
| 2025-10-09 10:00 | 5.96x | Small-body bullish | Flat / fading | 0.075% / 0.254% / -0.645% | Weak move without breakout | 51.8% | 21.8% | 26.4% | 2.86x | 0.467% / 0.775% |
| 2025-10-09 11:15 | 4.06x | Full-bodied bearish | Impulse -> reversal | 0.197% / 0.703% / 3.179% | False breakout | 98.1% | 0.4% | 1.5% | 2.89x | 1.175% / 3.862% |
| 2025-10-09 11:30 | 5.18x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.505% / 1.748% / 2.338% | True breakout | 11.9% | 7.1% | 81.0% | 1.96x | 3.657% / 0.190% |
| 2025-10-09 12:00 | 2.85x | Full-bodied bullish | Impulse / continuation | 1.207% / 0.580% / 1.628% | True breakout | 80.8% | 11.9% | 7.3% | 1.80x | 2.063% / 0.028% |
| 2025-10-09 12:15 | 3.54x | Full-bodied bullish | Flat / fading | -0.620% / -0.498% / -0.436% | Weak move without breakout | 64.5% | 35.1% | 0.4% | 2.11x | 0.845% / 1.063% |
| 2025-10-10 09:00 | 4.35x | Bearish pin-bar / upper rejection | Reversal | -0.095% / -0.142% / -0.264% | Liquidity sweep / reversal | 14.0% | 60.0% | 26.0% | 1.45x | 0.149% / 0.400% |
| 2025-10-10 09:15 | 3.44x | Bullish pin-bar / lower rejection | Reversal | -0.047% / 0.088% / -0.163% | Liquidity sweep / reversal | 19.6% | 0.0% | 80.4% | 1.55x | 0.305% / 0.244% |
| 2025-10-10 10:00 | 2.69x | Full-bodied bearish | Flat / fading | 0.007% / 0.000% / 0.061% | Weak move without breakout | 64.6% | 18.8% | 16.7% | 1.21x | 0.170% / 0.238% |
| 2025-10-10 10:15 | 2.81x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.007% / 0.129% / 0.305% | True breakout | 2.6% | 46.2% | 51.3% | 0.91x | 0.414% / 0.204% |
| 2025-10-10 10:30 | 2.56x | Bearish pin-bar / upper rejection | Reversal | 0.136% / 0.061% / 0.448% | Liquidity sweep / reversal | 1.9% | 51.9% | 46.3% | 1.24x | 0.197% / 0.570% |
| 2025-10-10 11:15 | 2.57x | Bullish pin-bar / lower rejection | Flat / fading | 0.135% / 0.034% / -0.068% | Weak move without breakout | 31.9% | 17.6% | 50.5% | 2.02x | 0.257% / 0.169% |
| 2025-10-10 13:30 | 2.93x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.088% / -0.048% / -0.116% | True breakout | 51.5% | 7.4% | 41.2% | 1.50x | 0.517% / 0.041% |
| 2025-10-10 13:45 | 2.21x | Bullish pin-bar / lower rejection | Flat / fading | 0.041% / 0.007% / -0.347% | Weak move without breakout | 19.2% | 0.0% | 80.8% | 1.67x | 0.545% / 0.129% |
| 2025-10-10 16:30 | 2.32x | Full-bodied bearish | Impulse -> reversal | 0.007% / -0.152% / 0.420% | False breakout | 82.7% | 11.5% | 5.8% | 0.87x | 0.510% / 0.434% |
| 2025-10-10 16:45 | 3.84x | Bullish pin-bar / lower rejection | Reversal | -0.158% / -0.062% / 0.255% | Liquidity sweep / reversal | 1.2% | 12.8% | 86.0% | 1.42x | 0.889% / 0.379% |
| 2025-10-11 10:00 | 2.94x | Bullish pin-bar / lower rejection | Flat / fading | -0.007% / 0.076% / -0.035% | Position building in range | 46.3% | 4.2% | 49.5% | 3.58x | 0.083% / 0.201% |
| 2025-10-11 17:45 | 4.51x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.014% / 0.028% / 0.138% | True breakout | 50.0% | 42.3% | 7.7% | 2.68x | 0.201% / 0.042% |
| 2025-10-11 18:30 | 5.96x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.041% / 0.249% / 0.449% | True breakout | 45.8% | 41.7% | 12.5% | 2.17x | 0.788% / 0.000% |
| 2025-10-11 18:45 | 2.60x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.207% / 0.470% / 0.463% | True breakout | 40.0% | 60.0% | 0.0% | 1.29x | 0.746% / -0.166% |
| 2025-10-12 10:00 | 10.26x | Bearish pin-bar / upper rejection | Flat / fading | -0.062% / -0.007% / -0.021% | Position building in range | 46.4% | 47.6% | 6.0% | 6.61x | 0.014% / 0.089% |
| 2025-10-12 18:15 | 3.75x | Small-body bearish | Reversal | 0.021% / 0.041% / 0.468% | Liquidity sweep / reversal | 45.0% | 20.0% | 35.0% | 2.75x | 0.041% / 0.530% |
| 2025-10-13 07:00 | 22.26x | Small-body bullish | Impulse / continuation | 0.000% / 0.075% / 0.144% | True breakout | 53.8% | 23.1% | 23.1% | 3.96x | 0.240% / 0.096% |
| 2025-10-13 07:15 | 4.89x | Bullish pin-bar / lower rejection | Reversal | 0.075% / 0.178% / 0.089% | Liquidity sweep / reversal | 5.3% | 21.1% | 73.7% | 1.56x | 0.021% / 0.240% |
| 2025-10-13 07:45 | 3.14x | Full-bodied bullish | Reversal | -0.034% / -0.089% / -0.260% | Liquidity sweep / reversal | 67.9% | 32.1% | 0.0% | 2.01x | 0.034% / 0.280% |
| 2025-10-13 08:15 | 3.65x | Small-body bearish | Impulse / continuation | -0.109% / -0.171% / -0.027% | True breakout | 34.6% | 34.6% | 30.8% | 1.59x | 0.431% / 0.089% |
| 2025-10-13 08:45 | 2.94x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.199% / 0.144% / 0.349% | False breakout | 31.0% | 58.6% | 10.3% | 1.52x | 0.260% / 0.514% |
| 2025-10-13 09:00 | 4.32x | Full-bodied bearish | Reversal | 0.343% / 0.481% / 0.769% | Liquidity sweep / reversal | 67.4% | 13.0% | 19.6% | 2.22x | 0.041% / 0.886% |
| 2025-10-13 09:15 | 3.73x | Full-bodied bullish | Impulse / continuation | 0.137% / 0.205% / 0.370% | True breakout | 83.3% | 6.7% | 10.0% | 2.52x | 0.541% / 0.062% |
| 2025-10-13 09:30 | 6.15x | Bearish pin-bar / upper rejection | Flat / fading | 0.068% / 0.287% / -0.082% | Weak move without breakout | 37.5% | 60.7% | 1.8% | 2.04x | 0.403% / 0.198% |
| 2025-10-13 10:00 | 6.38x | Bullish pin-bar / lower rejection | Reversal | -0.055% / -0.368% / -0.811% | Liquidity sweep / reversal | 34.1% | 19.3% | 46.6% | 2.79x | 0.041% / 1.090% |
| 2025-10-13 10:45 | 6.47x | Full-bodied bearish | Impulse / continuation | 0.076% / -0.488% / -0.103% | True breakout | 71.7% | 0.0% | 28.3% | 2.63x | 0.701% / 0.165% |
| 2025-10-13 11:15 | 3.07x | Full-bodied bearish | Flat / fading | -0.007% / 0.387% / -0.193% | Position building in range | 63.5% | 11.9% | 24.6% | 2.61x | 0.193% / 0.484% |
| 2025-10-13 14:45 | 2.25x | Full-bodied bullish | Impulse / continuation | 0.392% / 0.165% / 0.550% | True breakout | 61.8% | 35.0% | 3.3% | 1.82x | 0.852% / -0.014% |
| 2025-10-14 09:00 | 3.28x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.131% / -0.337% / -0.268% | True breakout | 59.0% | 0.0% | 41.0% | 1.73x | 0.489% / 0.007% |
| 2025-10-14 09:15 | 3.85x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.207% / -0.131% / 0.048% | True breakout | 39.6% | 2.1% | 58.3% | 2.06x | 0.358% / 0.248% |
| 2025-10-14 09:30 | 3.15x | Full-bodied bearish | Reversal | 0.076% / 0.069% / 0.221% | Liquidity sweep / reversal | 91.2% | 0.0% | 8.8% | 1.33x | 0.152% / 0.456% |
| 2025-10-14 09:45 | 3.35x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.007% / 0.179% / 0.228% | True breakout | 40.7% | 59.3% | 0.0% | 1.01x | 0.524% / 0.228% |
| 2025-10-14 10:00 | 6.67x | Doji | Impulse / continuation | 0.186% / 0.152% / 0.214% | True breakout | 0.0% | 48.4% | 51.6% | 2.33x | 0.531% / 0.531% |
| 2025-10-14 10:15 | 2.80x | Bearish pin-bar / upper rejection | Flat / fading | -0.034% / 0.048% / 0.007% | Weak move without breakout | 40.8% | 59.2% | 0.0% | 1.67x | 0.344% / 0.145% |
| 2025-10-14 10:45 | 4.91x | Bearish pin-bar / upper rejection | Reversal | -0.021% / -0.041% / 0.193% | Liquidity sweep / reversal | 18.3% | 60.6% | 21.1% | 2.22x | 0.255% / 0.193% |
| 2025-10-14 15:30 | 3.14x | Full-bodied bearish | Flat / fading | 0.193% / 0.083% / 0.035% | Weak move without breakout | 97.1% | 1.0% | 1.9% | 2.59x | 0.145% / 0.338% |
| 2025-10-14 15:45 | 3.31x | Small-body bullish | Reversal | -0.110% / -0.007% / -0.289% | Liquidity sweep / reversal | 48.3% | 36.2% | 15.5% | 1.30x | 0.103% / 0.338% |
| 2025-10-14 16:00 | 2.44x | Bullish pin-bar / lower rejection | Reversal | 0.103% / -0.048% / 0.145% | Liquidity sweep / reversal | 27.8% | 11.1% | 61.1% | 1.20x | 0.235% / 0.214% |
| 2025-10-14 18:00 | 2.38x | Bearish pin-bar / upper rejection | Reversal | 0.096% / -0.103% / -0.384% | Liquidity sweep / reversal | 45.9% | 52.7% | 1.4% | 1.61x | 0.137% / 0.411% |
| 2025-10-15 09:45 | 3.24x | Small-body bullish | Reversal | -0.021% / -0.420% / -0.262% | Liquidity sweep / reversal | 38.5% | 28.2% | 33.3% | 1.86x | 0.083% / 0.530% |
| 2025-10-15 10:00 | 3.92x | Doji / lower rejection | Impulse / continuation | -0.399% / -0.179% / -0.028% | True breakout | 0.0% | 39.5% | 60.5% | 1.73x | 0.509% / 0.509% |
| 2025-10-15 10:15 | 7.80x | Full-bodied bearish | Flat / fading | 0.221% / 0.159% / 0.359% | Weak move without breakout | 75.0% | 3.9% | 21.1% | 3.43x | 0.097% / 0.463% |
| 2025-10-15 10:30 | 3.48x | Small-body bullish | Flat / fading | -0.062% / 0.152% / -0.014% | Weak move without breakout | 48.4% | 25.8% | 25.8% | 2.25x | 0.241% / 0.166% |
| 2025-10-15 13:00 | 4.53x | Full-bodied bullish | Reversal | -0.247% / -0.261% / -0.419% | Liquidity sweep / reversal | 63.0% | 33.3% | 3.7% | 2.12x | 0.034% / 0.508% |
| 2025-10-15 14:30 | 2.75x | Full-bodied bullish | Impulse / continuation | 0.075% / 0.219% / 0.021% | True breakout | 78.0% | 16.5% | 5.5% | 2.47x | 0.411% / 0.062% |
| 2025-10-16 09:00 | 3.81x | Full-bodied bearish | Impulse / continuation | 0.028% / 0.034% / -0.166% | True breakout | 70.6% | 2.9% | 26.5% | 2.14x | 0.200% / 0.131% |
| 2025-10-16 10:00 | 8.64x | Bearish pin-bar / upper rejection | Reversal | 0.166% / 0.145% / 0.345% | Liquidity sweep / reversal | 45.8% | 43.8% | 10.4% | 2.88x | 0.028% / 0.449% |
| 2025-10-16 10:15 | 3.96x | Full-bodied bullish | Impulse / continuation | -0.021% / 0.062% / 0.028% | True breakout | 82.8% | 3.4% | 13.8% | 1.54x | 0.283% / 0.110% |
| 2025-10-16 10:45 | 2.85x | Bearish pin-bar / upper rejection | Reversal | 0.117% / -0.034% / 0.062% | Liquidity sweep / reversal | 31.6% | 60.5% | 7.9% | 1.89x | 0.221% / 0.221% |
| 2025-10-16 11:00 | 3.94x | Small-body bullish | Reversal | -0.151% / -0.213% / -0.055% | Liquidity sweep / reversal | 44.7% | 39.5% | 15.8% | 1.86x | 0.034% / 0.337% |
| 2025-10-16 14:30 | 2.80x | Bearish pin-bar / upper rejection | Reversal | -0.179% / -0.151% / 0.027% | Liquidity sweep / reversal | 27.3% | 72.7% | 0.0% | 1.19x | 0.144% / 0.206% |
| 2025-10-16 15:15 | 2.55x | Small-body bullish | Impulse / continuation | -0.007% / 0.089% / 0.254% | True breakout | 58.0% | 30.0% | 12.0% | 1.86x | 0.288% / 0.110% |
| 2025-10-16 17:00 | 9.45x | Full-bodied bullish | Impulse / continuation | 0.244% / 0.989% / 0.576% | True breakout | 84.3% | 12.7% | 2.9% | 7.14x | 1.531% / 0.210% |
| 2025-10-16 17:15 | 4.84x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.743% / 0.507% / 0.432% | True breakout | 31.0% | 42.2% | 26.7% | 2.75x | 1.284% / 0.027% |
| 2025-10-16 17:30 | 5.28x | Full-bodied bullish | Impulse / continuation | -0.235% / -0.409% / -0.114% | True breakout | 91.1% | 7.3% | 1.6% | 2.48x | 0.537% / 0.624% |
| 2025-10-16 17:45 | 3.49x | Bearish pin-bar / upper rejection | Flat / fading | -0.175% / -0.074% / 0.081% | Weak move without breakout | 31.5% | 61.3% | 7.3% | 2.23x | 0.390% / 0.282% |
| 2025-10-16 20:00 | 3.14x | Full-bodied bullish | Impulse / continuation | 0.995% / 0.652% / 0.843% | True breakout | 85.5% | 13.7% | 0.8% | 6.16x | 1.304% / 0.553% |
| 2025-10-16 20:15 | 3.89x | Small-body bullish | Flat / fading | -0.339% / -0.046% / -0.117% | Position building in range | 53.5% | 16.7% | 29.8% | 2.51x | 0.170% / 0.639% |
| 2025-10-17 14:15 | 3.71x | Small-body bullish | Flat / fading | -0.299% / -0.114% / 0.044% | Position building in range | 52.8% | 37.0% | 10.2% | 2.38x | 0.267% / 0.438% |
| 2025-10-19 10:00 | 12.77x | Small-body bearish | Impulse / continuation | -0.070% / -0.248% / -0.305% | True breakout | 51.1% | 36.2% | 12.8% | 7.08x | 0.546% / 0.013% |
| 2025-10-19 10:15 | 3.72x | Full-bodied bearish | Impulse / continuation | -0.178% / -0.286% / -0.273% | True breakout | 76.9% | 23.1% | 0.0% | 1.36x | 0.476% / 0.006% |
| 2025-10-19 10:30 | 4.90x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.108% / -0.057% / -0.165% | True breakout | 43.9% | 0.0% | 56.1% | 6.79x | 0.299% / 0.025% |
| 2025-10-19 10:45 | 3.50x | Bullish pin-bar / lower rejection | Flat / fading | 0.051% / 0.013% / -0.025% | Weak move without breakout | 34.0% | 6.0% | 60.0% | 3.61x | 0.089% / 0.134% |
| 2025-10-19 16:15 | 4.67x | Bullish pin-bar / lower rejection | Reversal | 0.064% / -0.032% / 0.096% | Liquidity sweep / reversal | 6.7% | 0.0% | 93.3% | 3.33x | 0.243% / 0.077% |
| 2025-10-19 17:15 | 2.61x | Bearish pin-bar / upper rejection | Flat / fading | 0.051% / 0.057% / 0.064% | Position building in range | 20.0% | 76.7% | 3.3% | 1.65x | 0.096% / 0.045% |
| 2025-10-19 18:30 | 2.57x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.006% / 0.115% / -0.325% | False breakout | 44.8% | 3.4% | 51.7% | 1.45x | 0.159% / 0.325% |
| 2025-10-20 07:00 | 5.07x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.350% / -0.134% / -0.083% | True breakout | 32.5% | 20.0% | 47.5% | 1.99x | 0.350% / 0.032% |
| 2025-10-20 08:15 | 3.09x | Bearish pin-bar / upper rejection | Reversal | -0.032% / -0.153% / -0.382% | Liquidity sweep / reversal | 60.0% | 40.0% | 0.0% | 1.20x | 0.013% / 0.446% |
| 2025-10-20 09:15 | 3.60x | Small-body bearish | Reversal | 0.064% / -0.026% / 0.754% | Liquidity sweep / reversal | 40.0% | 35.0% | 25.0% | 1.46x | 0.300% / 0.863% |
| 2025-10-20 09:45 | 3.38x | Bullish pin-bar / lower rejection | Reversal | 0.729% / 0.780% / 0.882% | Liquidity sweep / reversal | 31.8% | 22.7% | 45.5% | 1.45x | 0.275% / 1.387% |
| 2025-10-20 10:00 | 14.02x | Full-bodied bullish | Impulse / continuation | 0.051% / 0.501% / 0.121% | True breakout | 67.8% | 11.3% | 20.9% | 5.63x | 0.654% / 0.165% |
| 2025-10-20 10:15 | 5.81x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.450% / 0.102% / 0.165% | True breakout | 21.6% | 33.3% | 45.1% | 1.16x | 0.603% / 0.051% |
| 2025-10-20 10:30 | 8.79x | Full-bodied bullish | Flat / fading | -0.347% / -0.379% / -0.278% | Position building in range | 68.9% | 23.3% | 7.8% | 2.23x | 0.095% / 0.467% |
| 2025-10-20 10:45 | 2.57x | Full-bodied bearish | Flat / fading | -0.032% / 0.063% / 0.032% | Weak move without breakout | 74.7% | 13.3% | 12.0% | 1.48x | 0.120% / 0.444% |
| 2025-10-20 11:00 | 2.99x | Bearish pin-bar / upper rejection | Reversal | 0.095% / 0.101% / -0.273% | Liquidity sweep / reversal | 11.2% | 82.5% | 6.3% | 1.54x | 0.311% / 0.197% |
| 2025-10-20 22:30 | 3.84x | Doji | Flat / fading | 0.013% / 0.025% / -0.051% | Position building in range | 0.0% | 52.6% | 47.4% | 1.87x | 0.057% / 0.057% |
| 2025-10-21 07:00 | 12.31x | Full-bodied bearish | Impulse / continuation | -0.805% / -1.821% / -1.668% | True breakout | 88.7% | 0.0% | 11.3% | 8.48x | 2.402% / 0.058% |
| 2025-10-21 07:15 | 10.39x | Full-bodied bearish | Impulse / continuation | -1.024% / -0.657% / -0.670% | True breakout | 83.8% | 7.4% | 8.8% | 10.16x | 1.610% / 0.109% |
| 2025-10-21 07:30 | 17.50x | Full-bodied bearish | Flat / fading | 0.371% / 0.156% / 0.508% | Position building in range | 60.7% | 5.2% | 34.1% | 10.80x | 0.371% / 0.670% |
| 2025-10-21 07:45 | 4.67x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.214% / -0.013% / 0.266% | True breakout | 56.5% | 0.9% | 42.6% | 2.68x | 0.376% / 0.519% |
| 2025-10-21 09:00 | 3.48x | Small-body bearish | Reversal | 0.305% / -0.123% / 0.292% | Liquidity sweep / reversal | 36.5% | 27.8% | 35.7% | 1.85x | 0.162% / 0.441% |
| 2025-10-21 17:00 | 2.80x | Full-bodied bearish | Impulse / continuation | -0.111% / -0.380% / -2.785% | True breakout | 69.2% | 0.0% | 30.8% | 2.15x | 2.936% / 0.170% |
| 2025-10-21 17:45 | 2.54x | Full-bodied bearish | Impulse / continuation | -2.021% / -1.381% / -1.017% | True breakout | 70.5% | 26.1% | 3.4% | 1.90x | 2.173% / -0.007% |
| 2025-10-21 18:00 | 10.10x | Full-bodied bearish | Flat / fading | 0.654% / 0.971% / 1.369% | Position building in range | 93.0% | 0.0% | 7.0% | 6.41x | 0.148% / 1.584% |
| 2025-10-21 18:15 | 4.68x | Full-bodied bullish | Impulse / continuation | 0.315% / 0.368% / 0.804% | True breakout | 73.5% | 9.8% | 16.7% | 1.82x | 1.011% / 0.201% |
| 2025-10-22 09:30 | 2.60x | Full-bodied bullish | Reversal | -0.318% / -0.543% / -0.265% | Liquidity sweep / reversal | 77.9% | 3.9% | 18.2% | 1.72x | -0.007% / 0.749% |
| 2025-10-22 10:00 | 3.12x | Small-body bearish | Reversal | -0.013% / 0.280% / -0.033% | Liquidity sweep / reversal | 54.4% | 26.5% | 19.1% | 1.68x | 0.206% / 0.393% |
| 2025-10-22 10:30 | 2.50x | Small-body bullish | Reversal | -0.179% / -0.312% / -0.040% | Liquidity sweep / reversal | 48.9% | 18.9% | 32.2% | 1.98x | 0.193% / 0.777% |
| 2025-10-22 11:15 | 2.81x | Bullish pin-bar / lower rejection | Reversal | 0.367% / 0.407% / 0.367% | Liquidity sweep / reversal | 21.3% | 4.0% | 74.7% | 1.76x | -0.007% / 0.600% |
| 2025-10-22 14:00 | 2.02x | Bullish pin-bar / lower rejection | Flat / fading | -0.409% / -0.255% / -0.463% | Weak move without breakout | 53.6% | 0.0% | 46.4% | 1.40x | 0.509% / 0.074% |
| 2025-10-22 16:30 | 1.96x | Full-bodied bullish | Flat / fading | 0.000% / 0.020% / -0.354% | Weak move without breakout | 75.5% | 20.6% | 3.9% | 1.84x | 0.200% / 0.367% |
| 2025-10-22 22:00 | 12.75x | Full-bodied bearish | Impulse / continuation | -0.360% / 0.272% / -0.204% | True breakout | 70.9% | 0.9% | 28.2% | 8.11x | 0.754% / 0.482% |
| 2025-10-22 22:15 | 7.14x | Small-body bearish | Reversal | 0.634% / 0.607% / 0.777% | Liquidity sweep / reversal | 33.7% | 30.0% | 36.3% | 3.71x | 0.218% / 1.507% |
| 2025-10-22 22:30 | 6.14x | Full-bodied bullish | Impulse / continuation | -0.027% / -0.474% / 0.088% | True breakout | 73.6% | 0.0% | 26.4% | 2.33x | 0.867% / 0.671% |
| 2025-10-22 23:00 | 3.35x | Full-bodied bearish | Reversal | 0.620% / 0.565% / -1.293% | Liquidity sweep / reversal | 72.4% | 0.0% | 27.6% | 1.75x | 1.293% / 1.348% |
| 2025-10-22 23:15 | 3.03x | Bearish pin-bar / upper rejection | Reversal | -0.054% / 0.135% / -0.995% | Liquidity sweep / reversal | 41.9% | 49.3% | 8.8% | 3.32x | 0.230% / 1.901% |
| 2025-10-23 07:00 | 3.03x | Full-bodied bullish | Flat / fading | -0.362% / -0.396% / -0.362% | Position building in range | 91.8% | 8.2% | 0.0% | 1.49x | 0.034% / 0.670% |
| 2025-10-23 18:30 | 5.67x | Small-body bullish | Flat / fading | 0.000% / -0.265% / -0.177% | Position building in range | 54.1% | 39.5% | 6.4% | 4.17x | 0.109% / 0.448% |
| 2025-10-24 09:00 | 3.22x | Full-bodied bearish | Flat / fading | 0.020% / 0.081% / -0.149% | Weak move without breakout | 68.4% | 18.4% | 13.2% | 1.42x | 0.183% / 0.142% |
| 2025-10-24 10:00 | 2.71x | Small-body bearish | Impulse / continuation | -0.176% / -0.284% / -0.400% | True breakout | 56.8% | 31.8% | 11.4% | 1.69x | 0.616% / 0.061% |
| 2025-10-24 10:45 | 2.95x | Full-bodied bearish | Flat / fading | 0.143% / 0.082% / 0.123% | Position building in range | 69.8% | 9.4% | 20.8% | 1.80x | 0.061% / 0.259% |
| 2025-10-24 12:15 | 2.69x | Small-body bearish | Reversal | 0.055% / -0.055% / 0.477% | Liquidity sweep / reversal | 52.6% | 7.9% | 39.5% | 2.24x | 0.280% / 0.934% |
| 2025-10-24 13:15 | 2.98x | Bearish pin-bar / upper rejection | Reversal | -0.970% / -1.371% / -1.282% | Liquidity sweep / reversal | 18.4% | 53.6% | 28.0% | 2.76x | 1.534% / 1.608% |
| 2025-10-24 13:30 | 18.44x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.404% / -0.315% / 0.014% | True breakout | 37.2% | 58.1% | 4.7% | 7.36x | 0.644% / 0.171% |
| 2025-10-24 13:45 | 4.44x | Small-body bearish | Flat / fading | 0.089% / 0.089% / 0.323% | Weak move without breakout | 54.8% | 18.3% | 27.0% | 1.49x | 0.241% / 0.578% |
| 2025-10-27 07:00 | 8.24x | Full-bodied bearish | Impulse / continuation | -0.533% / -0.326% / -0.443% | True breakout | 68.0% | 3.0% | 29.0% | 4.71x | 0.741% / 0.000% |
| 2025-10-27 07:15 | 5.73x | Full-bodied bearish | Flat / fading | 0.209% / 0.146% / 0.195% | Position building in range | 72.0% | 0.0% | 28.0% | 3.91x | 0.091% / 0.285% |
| 2025-10-27 09:00 | 4.07x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.320% / -0.313% / -0.167% | True breakout | 14.7% | 13.2% | 72.1% | 1.69x | 1.537% / 0.028% |
| 2025-10-27 09:45 | 6.12x | Bullish pin-bar / lower rejection | Reversal | 0.737% / 0.555% / 0.702% | Liquidity sweep / reversal | 43.6% | 7.4% | 48.9% | 3.91x | 0.316% / 0.863% |
| 2025-10-27 10:00 | 5.37x | Full-bodied bullish | Flat / fading | -0.181% / -0.049% / -0.091% | Weak move without breakout | 69.5% | 0.7% | 29.8% | 2.54x | 0.125% / 0.383% |
| 2025-10-27 10:15 | 2.59x | Bullish pin-bar / lower rejection | Flat / fading | 0.133% / 0.147% / 0.014% | Weak move without breakout | 47.3% | 0.0% | 52.7% | 0.81x | 0.133% / 0.307% |
| 2025-10-27 14:45 | 2.69x | Bullish pin-bar / lower rejection | Reversal | 0.127% / 0.466% / 0.537% | Liquidity sweep / reversal | 27.1% | 9.4% | 63.5% | 1.85x | 0.141% / 0.721% |
| 2025-10-27 23:30 | 4.13x | Bullish pin-bar / lower rejection | Flat / fading | 0.120% / 0.233% / 0.106% | Weak move without breakout | 54.7% | 0.0% | 45.3% | 3.21x | 0.255% / 0.262% |
| 2025-10-28 07:00 | 5.67x | Bullish pin-bar / lower rejection | Reversal | 0.078% / 0.014% / 0.219% | Liquidity sweep / reversal | 45.2% | 0.0% | 54.8% | 3.07x | 0.078% / 0.481% |
| 2025-10-28 09:00 | 7.37x | Full-bodied bullish | Impulse / continuation | -0.168% / -0.077% / 0.049% | True breakout | 98.1% | 1.9% | 0.0% | 3.02x | 0.343% / 0.406% |
| 2025-10-28 09:45 | 2.52x | Bullish pin-bar / lower rejection | Reversal | -0.042% / -0.161% / 0.063% | Liquidity sweep / reversal | 23.9% | 22.8% | 53.3% | 2.14x | 0.252% / 0.301% |
| 2025-10-28 11:00 | 6.46x | Full-bodied bullish | Impulse / continuation | 0.270% / 0.562% / 1.366% | True breakout | 86.8% | 8.3% | 5.0% | 2.48x | 1.366% / 0.076% |
| 2025-10-28 11:15 | 2.95x | Small-body bullish | Impulse / continuation | 0.290% / 0.754% / 0.816% | True breakout | 53.5% | 29.6% | 16.9% | 1.28x | 1.120% / 0.187% |
| 2025-10-28 11:30 | 2.64x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.462% / 0.800% / 0.931% | True breakout | 52.0% | 8.0% | 40.0% | 1.31x | 0.931% / 0.090% |
| 2025-10-28 11:45 | 4.46x | Full-bodied bullish | Impulse / continuation | 0.336% / 0.062% / 0.329% | True breakout | 81.3% | 12.1% | 6.6% | 1.53x | 0.535% / 0.206% |
| 2025-10-29 09:00 | 3.81x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.198% / -0.294% / 0.205% | False breakout | 19.0% | 11.9% | 69.0% | 2.02x | 0.376% / 0.431% |
| 2025-10-29 09:45 | 3.81x | Full-bodied bullish | Impulse / continuation | 0.239% / 0.301% / 0.185% | True breakout | 67.9% | 17.9% | 14.3% | 2.25x | 0.465% / 0.123% |
| 2025-10-29 10:00 | 10.40x | Small-body bullish | Flat / fading | 0.061% / -0.123% / -0.041% | Position building in range | 39.5% | 38.4% | 22.1% | 3.06x | 0.218% / 0.246% |
| 2025-10-29 10:15 | 3.37x | Bearish pin-bar / upper rejection | Reversal | -0.184% / -0.116% / -0.102% | Liquidity sweep / reversal | 8.5% | 48.9% | 42.6% | 1.42x | 0.136% / 0.307% |
| 2025-10-29 14:00 | 2.20x | Bearish pin-bar / upper rejection | Reversal | -0.225% / -0.320% / -0.054% | Liquidity sweep / reversal | 51.5% | 40.9% | 7.6% | 1.86x | 0.143% / 0.436% |
| 2025-10-30 07:00 | 2.96x | Full-bodied bearish | Impulse / continuation | -0.219% / -0.137% / -0.068% | True breakout | 82.5% | 12.5% | 5.0% | 2.57x | 0.383% / 0.089% |
| 2025-10-30 07:15 | 3.14x | Small-body bearish | Flat / fading | 0.082% / 0.199% / 0.096% | Weak move without breakout | 48.4% | 24.2% | 27.4% | 3.49x | 0.165% / 0.295% |
| 2025-10-30 09:00 | 2.60x | Full-bodied bullish | Impulse / continuation | 0.157% / 0.321% / 0.841% | True breakout | 90.0% | 0.0% | 10.0% | 1.81x | 0.984% / 0.082% |
| 2025-10-30 09:15 | 4.76x | Small-body bullish | Impulse / continuation | 0.164% / 0.341% / 0.730% | True breakout | 54.5% | 20.5% | 25.0% | 1.81x | 0.976% / 0.089% |
| 2025-10-30 09:30 | 3.40x | Full-bodied bullish | Impulse / continuation | 0.177% / 0.518% / 0.674% | True breakout | 62.5% | 7.5% | 30.0% | 1.50x | 0.811% / 0.000% |
| 2025-10-30 09:45 | 7.52x | Full-bodied bullish | Impulse / continuation | 0.340% / 0.388% / 0.211% | True breakout | 68.4% | 31.6% | 0.0% | 1.31x | 0.653% / -0.020% |
| 2025-10-30 10:00 | 11.76x | Full-bodied bullish | Flat / fading | 0.047% / 0.156% / -0.034% | Weak move without breakout | 69.1% | 30.9% | 0.0% | 2.27x | 0.312% / 0.156% |
| 2025-10-30 10:15 | 4.97x | Bearish pin-bar / upper rejection | Reversal | 0.108% / -0.176% / -0.041% | Liquidity sweep / reversal | 12.1% | 54.5% | 33.3% | 1.97x | 0.264% / 0.196% |
| 2025-10-30 10:45 | 2.80x | Full-bodied bearish | Flat / fading | 0.095% / 0.136% / 0.258% | Weak move without breakout | 63.2% | 32.4% | 4.4% | 1.84x | 0.020% / 0.523% |
| 2025-10-30 12:15 | 4.09x | Full-bodied bullish | Flat / fading | 0.121% / 0.007% / -0.309% | Position building in range | 74.4% | 23.3% | 2.3% | 3.01x | 0.175% / 0.309% |
| 2025-10-31 07:15 | 3.25x | Small-body bullish | Flat / fading | 0.100% / 0.207% / -0.100% | Weak move without breakout | 37.5% | 37.5% | 25.0% | 1.67x | 0.234% / 0.167% |
| 2025-10-31 10:00 | 3.76x | Full-bodied bearish | Impulse / continuation | 0.074% / -0.242% / -0.181% | True breakout | 68.8% | 12.5% | 18.7% | 1.27x | 0.450% / 0.155% |
| 2025-10-31 10:30 | 4.78x | Small-body bearish | Flat / fading | -0.054% / 0.061% / -0.310% | Weak move without breakout | 53.0% | 9.6% | 37.3% | 2.02x | 0.418% / 0.236% |
| 2025-10-31 10:45 | 2.69x | Bearish pin-bar / upper rejection | Reversal | 0.115% / 0.155% / -0.108% | Liquidity sweep / reversal | 17.8% | 44.4% | 37.8% | 1.12x | 0.364% / 0.290% |
| 2025-10-31 11:30 | 2.65x | Full-bodied bearish | Flat / fading | 0.149% / 0.176% / 0.270% | Position building in range | 78.2% | 1.3% | 20.5% | 1.86x | 0.088% / 0.351% |
| 2025-10-31 14:15 | 1.99x | Full-bodied bearish | Flat / fading | 0.176% / 0.278% / 0.278% | Weak move without breakout | 77.6% | 2.6% | 19.7% | 1.83x | 0.156% / 0.406% |
| 2025-10-31 20:00 | 11.52x | Full-bodied bearish | Flat / fading | 0.068% / 0.116% / 0.218% | Position building in range | 72.4% | 2.3% | 25.3% | 6.53x | 0.198% / 0.314% |
| 2025-11-01 10:00 | 2.54x | Full-bodied bullish | Impulse / continuation | -0.068% / 0.142% / 0.231% | True breakout | 74.3% | 11.4% | 14.3% | 1.10x | 0.366% / 0.129% |
| 2025-11-01 10:45 | 5.35x | Full-bodied bullish | Reversal | -0.061% / 0.007% / -0.156% | Liquidity sweep / reversal | 62.9% | 31.4% | 5.7% | 1.09x | 0.074% / 0.216% |
| 2025-11-01 22:45 | 3.56x | Bullish pin-bar / lower rejection | Reversal | 0.109% / -0.143% / -0.027% | Liquidity sweep / reversal | 44.0% | 8.0% | 48.0% | 3.80x | 0.387% / 0.115% |
| 2025-11-01 23:15 | 4.50x | Full-bodied bearish | Impulse -> reversal | -0.007% / 0.116% / 0.578% | False breakout | 72.5% | 2.0% | 25.5% | 5.49x | 0.245% / 0.769% |
| 2025-11-01 23:30 | 3.71x | Bullish pin-bar / lower rejection | Reversal | 0.122% / 0.422% / 0.585% | Liquidity sweep / reversal | 2.3% | 18.2% | 79.5% | 3.52x | 0.088% / 0.776% |
| 2025-11-03 07:00 | 3.58x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / 0.007% / 0.237% | Weak move without breakout | 40.7% | 47.5% | 11.9% | 3.11x | 0.311% / 0.074% |
| 2025-11-03 07:45 | 2.58x | Full-bodied bullish | Flat / fading | 0.007% / 0.061% / 0.034% | Position building in range | 73.3% | 26.7% | 0.0% | 1.89x | 0.074% / 0.067% |
| 2025-11-03 09:00 | 7.82x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.067% / 0.558% | True breakout | 60.4% | 39.6% | 0.0% | 3.37x | 0.665% / 0.067% |
| 2025-11-03 10:00 | 7.69x | Full-bodied bullish | Impulse / continuation | -0.080% / 0.261% / 0.100% | True breakout | 76.2% | 20.0% | 3.8% | 2.69x | 0.348% / 0.187% |
| 2025-11-03 10:30 | 6.27x | Full-bodied bullish | Flat / fading | -0.040% / -0.160% / -0.320% | Position building in range | 63.8% | 16.2% | 20.0% | 2.46x | 0.067% / 0.400% |
| 2025-11-03 21:45 | 5.95x | Small-body bearish | Flat / fading | -0.013% / -0.007% / -0.047% | Weak move without breakout | 58.1% | 3.2% | 38.7% | 3.53x | 0.087% / 0.047% |
| 2025-11-05 07:00 | 9.63x | Bullish pin-bar / lower rejection | Flat / fading | -0.175% / -0.107% / 0.081% | Position building in range | 41.4% | 0.0% | 58.6% | 10.41x | 0.222% / 0.114% |
| 2025-11-05 07:15 | 2.57x | Full-bodied bearish | Reversal | 0.067% / 0.047% / 0.114% | Liquidity sweep / reversal | 70.3% | 29.7% | 0.0% | 1.57x | 0.047% / 0.289% |
| 2025-11-05 08:00 | 2.77x | Full-bodied bullish | Impulse / continuation | -0.141% / -0.067% / 0.315% | True breakout | 62.0% | 10.0% | 28.0% | 1.83x | 0.470% / 0.168% |
| 2025-11-05 08:45 | 3.00x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.282% / 0.295% / 0.208% | True breakout | 25.0% | 58.3% | 16.7% | 2.01x | 0.436% / 0.020% |
| 2025-11-05 09:00 | 4.31x | Full-bodied bullish | Reversal | 0.013% / -0.120% / -0.355% | Liquidity sweep / reversal | 60.3% | 33.8% | 5.9% | 2.03x | 0.154% / 0.442% |
| 2025-11-05 09:30 | 2.57x | Bullish pin-bar / lower rejection | Flat / fading | 0.047% / -0.234% / 0.007% | Weak move without breakout | 38.8% | 12.2% | 49.0% | 1.29x | 0.322% / 0.127% |
| 2025-11-05 10:00 | 2.90x | Full-bodied bearish | Reversal | 0.215% / 0.242% / 0.873% | Liquidity sweep / reversal | 66.1% | 12.9% | 21.0% | 1.49x | 0.027% / 0.873% |
| 2025-11-05 11:00 | 3.54x | Full-bodied bullish | Impulse / continuation | -0.047% / -0.160% / -0.053% | True breakout | 91.5% | 0.0% | 8.5% | 2.52x | 0.260% / 0.226% |
| 2025-11-05 11:15 | 4.61x | Bearish pin-bar / upper rejection | Flat / fading | -0.113% / 0.007% / -0.213% | Weak move without breakout | 13.7% | 76.5% | 9.8% | 1.19x | 0.306% / 0.153% |
| 2025-11-05 13:30 | 3.75x | Full-bodied bullish | Flat / fading | -0.046% / -0.086% / 0.100% | Weak move without breakout | 62.2% | 35.1% | 2.7% | 1.87x | 0.232% / 0.093% |
| 2025-11-05 16:45 | 2.75x | Full-bodied bearish | Impulse / continuation | -0.067% / -0.580% / -0.460% | True breakout | 89.7% | 6.9% | 3.4% | 2.79x | 0.720% / 0.173% |
| 2025-11-05 17:15 | 3.50x | Full-bodied bearish | Impulse / continuation | 0.201% / 0.121% / -0.342% | True breakout | 64.6% | 16.8% | 18.6% | 3.28x | 0.496% / 0.362% |
| 2025-11-06 07:00 | 4.46x | Small-body bullish | Flat / fading | 0.054% / 0.067% / -0.007% | Position building in range | 46.7% | 36.7% | 16.7% | 3.61x | 0.148% / 0.027% |
| 2025-11-06 10:00 | 3.64x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.195% / -0.215% / -0.376% | True breakout | 30.0% | 26.7% | 43.3% | 1.37x | 0.678% / 0.081% |
| 2025-11-06 10:15 | 2.86x | Full-bodied bearish | Impulse / continuation | -0.020% / -0.256% / -0.256% | True breakout | 67.4% | 27.9% | 4.7% | 1.85x | 0.484% / 0.087% |
| 2025-11-06 10:45 | 2.61x | Small-body bearish | Impulse / continuation | 0.074% / 0.000% / -0.519% | True breakout | 55.6% | 15.3% | 29.2% | 3.20x | 0.566% / 0.108% |
| 2025-11-06 11:00 | 3.17x | Bullish pin-bar / lower rejection | Reversal | -0.074% / -0.559% / -0.505% | Liquidity sweep / reversal | 24.0% | 10.0% | 66.0% | 1.90x | 0.034% / 0.640% |
| 2025-11-06 11:30 | 4.14x | Full-bodied bearish | Impulse / continuation | -0.034% / 0.054% / 0.034% | True breakout | 84.5% | 11.9% | 3.6% | 2.82x | 0.251% / 0.149% |
| 2025-11-06 11:45 | 2.65x | Bearish pin-bar / upper rejection | Reversal | 0.088% / -0.142% / 0.108% | Liquidity sweep / reversal | 14.7% | 64.7% | 20.6% | 1.00x | 0.217% / 0.142% |
| 2025-11-06 20:45 | 3.52x | Full-bodied bullish | Flat / fading | -0.074% / -0.067% / -0.013% | Position building in range | 66.7% | 26.7% | 6.7% | 2.02x | 0.081% / 0.081% |
| 2025-11-07 07:00 | 6.48x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.264% / 0.135% / -0.014% | True breakout | 4.3% | 14.4% | 81.3% | 8.14x | 0.325% / 0.203% |
| 2025-11-07 10:00 | 7.39x | Full-bodied bullish | Flat / fading | 0.155% / 0.013% / -0.094% | Weak move without breakout | 82.5% | 17.5% | 0.0% | 2.10x | 0.282% / 0.148% |
| 2025-11-07 10:15 | 3.11x | Small-body bullish | Reversal | -0.141% / -0.255% / -0.389% | Liquidity sweep / reversal | 46.9% | 26.5% | 26.5% | 1.14x | 0.128% / 0.584% |
| 2025-11-07 17:15 | 3.22x | Full-bodied bullish | Flat / fading | -0.034% / 0.007% / -0.141% | Position building in range | 67.6% | 32.4% | 0.0% | 1.96x | 0.034% / 0.148% |
| 2025-11-07 20:45 | 5.44x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.262% / -0.356% / -0.188% | True breakout | 32.8% | 50.0% | 17.2% | 3.92x | 0.397% / 0.007% |
| 2025-11-07 21:00 | 4.64x | Full-bodied bearish | Flat / fading | -0.094% / 0.094% / 0.047% | Weak move without breakout | 74.1% | 0.0% | 25.9% | 3.30x | 0.135% / 0.196% |
| 2025-11-08 15:00 | 2.99x | Full-bodied bullish | Reversal | -0.027% / -0.020% / -0.047% | Liquidity sweep / reversal | 66.7% | 11.1% | 22.2% | 1.58x | 0.007% / 0.047% |
| 2025-11-09 10:00 | 3.36x | Full-bodied bearish | Flat / fading | 0.034% / 0.034% / 0.027% | Position building in range | 84.2% | 0.0% | 15.8% | 2.96x | 0.020% / 0.047% |
| 2025-11-09 14:45 | 3.00x | Small-body bearish | Reversal | 0.013% / 0.007% / 0.007% | Liquidity sweep / reversal | 50.0% | 25.0% | 25.0% | 1.04x | 0.007% / 0.020% |
| 2025-11-10 07:00 | 64.99x | Full-bodied bullish | Flat / fading | -0.040% / -0.073% / -0.073% | Position building in range | 83.7% | 15.2% | 1.1% | 18.40x | 0.033% / 0.214% |
| 2025-11-10 07:15 | 3.69x | Small-body bearish | Reversal | -0.033% / 0.060% / -0.040% | Liquidity sweep / reversal | 37.5% | 31.2% | 31.2% | 1.42x | 0.174% / 0.074% |
| 2025-11-10 07:45 | 2.80x | Bullish pin-bar / lower rejection | Reversal | -0.094% / -0.100% / -0.100% | Liquidity sweep / reversal | 37.1% | 0.0% | 62.9% | 2.62x | 0.000% / 0.154% |
| 2025-11-10 09:00 | 4.45x | Bearish pin-bar / upper rejection | Reversal | 0.134% / 0.147% / 0.415% | Liquidity sweep / reversal | 44.1% | 44.1% | 11.8% | 1.92x | 0.054% / 0.643% |
| 2025-11-10 09:15 | 2.65x | Full-bodied bullish | Impulse / continuation | 0.013% / 0.094% / 0.401% | True breakout | 67.7% | 9.7% | 22.6% | 1.56x | 0.508% / 0.100% |
| 2025-11-10 09:45 | 5.19x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.187% / 0.307% / 0.407% | True breakout | 21.6% | 43.2% | 35.1% | 1.60x | 0.481% / 0.027% |
| 2025-11-10 10:00 | 6.16x | Bearish pin-bar / upper rejection | Flat / fading | 0.120% / 0.260% / 0.100% | Weak move without breakout | 39.4% | 51.5% | 9.1% | 2.60x | 0.293% / 0.013% |
| 2025-11-10 10:15 | 3.18x | Full-bodied bullish | Flat / fading | 0.140% / 0.100% / -0.040% | Weak move without breakout | 60.6% | 39.4% | 0.0% | 1.11x | 0.173% / 0.120% |
| 2025-11-10 11:30 | 2.58x | Full-bodied bearish | Flat / fading | 0.007% / 0.127% / -0.154% | Weak move without breakout | 65.3% | 2.0% | 32.7% | 1.78x | 0.200% / 0.207% |
| 2025-11-11 07:00 | 4.37x | Bearish pin-bar / upper rejection | Reversal | -0.324% / -0.283% / -0.182% | Liquidity sweep / reversal | 14.7% | 61.8% | 23.5% | 2.62x | 0.000% / 0.485% |
| 2025-11-11 07:15 | 2.51x | Full-bodied bearish | Flat / fading | 0.041% / -0.014% / 0.081% | Position building in range | 66.7% | 0.0% | 33.3% | 5.09x | 0.088% / 0.162% |
| 2025-11-11 10:00 | 4.62x | Bearish pin-bar / upper rejection | Reversal | 0.162% / 0.189% / 0.128% | Liquidity sweep / reversal | 39.5% | 60.5% | 0.0% | 1.69x | 0.061% / 0.534% |
| 2025-11-11 10:15 | 3.50x | Small-body bullish | Impulse / continuation | 0.027% / 0.169% / 0.061% | True breakout | 53.3% | 26.7% | 20.0% | 1.62x | 0.371% / 0.074% |
| 2025-11-11 10:45 | 3.23x | Bearish pin-bar / upper rejection | Reversal | -0.202% / -0.108% / -0.148% | Liquidity sweep / reversal | 40.7% | 55.6% | 3.7% | 1.82x | 0.034% / 0.229% |
| 2025-11-11 14:45 | 4.11x | Bearish pin-bar / upper rejection | Flat / fading | 0.101% / 0.114% / 0.081% | Position building in range | 47.6% | 52.4% | 0.0% | 2.74x | 0.161% / 0.027% |
| 2025-11-11 16:00 | 3.57x | Small-body bullish | Flat / fading | -0.034% / -0.107% / -0.020% | Position building in range | 52.9% | 35.3% | 11.8% | 2.14x | 0.114% / 0.128% |
| 2025-11-11 20:45 | 2.95x | Bearish pin-bar / upper rejection | Reversal | -0.067% / -0.067% / -0.060% | Liquidity sweep / reversal | 47.1% | 44.1% | 8.8% | 1.87x | 0.020% / 0.262% |
| 2025-11-12 07:00 | 3.30x | Small-body bearish | Flat / fading | 0.000% / -0.027% / 0.034% | Position building in range | 27.1% | 35.6% | 37.3% | 4.28x | 0.101% / 0.034% |
| 2025-11-12 10:00 | 7.74x | Full-bodied bearish | Flat / fading | -0.013% / 0.020% / -0.081% | Weak move without breakout | 65.5% | 20.0% | 14.5% | 3.39x | 0.121% / 0.067% |
| 2025-11-12 10:15 | 2.92x | Bullish pin-bar / lower rejection | Reversal | 0.034% / 0.007% / -0.088% | Liquidity sweep / reversal | 9.5% | 23.8% | 66.7% | 1.08x | 0.209% / 0.081% |
| 2025-11-12 10:45 | 2.77x | Bullish pin-bar / lower rejection | Flat / fading | -0.074% / -0.094% / -0.027% | Weak move without breakout | 17.4% | 8.7% | 73.9% | 1.35x | 0.215% / 0.034% |
| 2025-11-12 15:00 | 4.94x | Full-bodied bearish | Impulse / continuation | -0.068% / -0.088% / -0.223% | True breakout | 89.6% | 0.0% | 10.4% | 3.30x | 0.460% / 0.122% |
| 2025-11-12 15:30 | 3.48x | Bullish pin-bar / lower rejection | Flat / fading | -0.020% / -0.135% / -0.081% | Weak move without breakout | 4.8% | 7.9% | 87.3% | 2.55x | 0.210% / 0.210% |
| 2025-11-13 09:00 | 7.09x | Full-bodied bullish | Flat / fading | -0.027% / -0.081% / -0.081% | Weak move without breakout | 60.0% | 11.1% | 28.9% | 3.06x | 0.081% / 0.257% |
| 2025-11-13 10:00 | 4.18x | Small-body bullish | Reversal | -0.061% / -0.156% / 0.271% | Liquidity sweep / reversal | 34.1% | 36.6% | 29.3% | 2.28x | 0.352% / 0.386% |
| 2025-11-13 10:30 | 3.86x | Bullish pin-bar / lower rejection | Reversal | 0.014% / 0.427% / 0.440% | Liquidity sweep / reversal | 27.1% | 15.3% | 57.6% | 3.00x | 0.217% / 0.589% |
| 2025-11-13 10:45 | 3.53x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.413% / 0.481% / 0.616% | True breakout | 7.9% | 10.5% | 81.6% | 1.72x | 0.643% / 0.061% |
| 2025-11-13 11:00 | 5.91x | Full-bodied bullish | Flat / fading | 0.067% / 0.013% / 0.067% | Weak move without breakout | 72.0% | 14.6% | 13.4% | 3.41x | 0.243% / 0.094% |
| 2025-11-13 11:15 | 2.59x | Small-body bullish | Flat / fading | -0.054% / 0.135% / -0.088% | Weak move without breakout | 34.2% | 36.8% | 28.9% | 1.31x | 0.175% / 0.182% |
| 2025-11-13 21:00 | 4.10x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.095% / -0.095% | Liquidity sweep / reversal | 17.9% | 78.6% | 3.6% | 2.18x | 0.007% / 0.142% |
| 2025-11-14 09:30 | 2.67x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.014% / 0.000% / 0.007% | True breakout | 44.4% | 50.0% | 5.6% | 1.36x | 0.196% / 0.095% |
| 2025-11-14 10:00 | 3.18x | Bullish pin-bar / lower rejection | Reversal | 0.108% / 0.007% / -0.182% | Liquidity sweep / reversal | 4.3% | 34.8% | 60.9% | 1.62x | 0.230% / 0.196% |
| 2025-11-14 10:15 | 4.30x | Full-bodied bullish | Reversal | -0.101% / -0.121% / -0.796% | Liquidity sweep / reversal | 62.5% | 37.5% | 0.0% | 1.56x | 0.088% / 0.877% |
| 2025-11-14 10:45 | 3.85x | Bearish pin-bar / upper rejection | Reversal | -0.169% / -0.675% / -0.540% | Liquidity sweep / reversal | 3.1% | 65.6% | 31.2% | 1.88x | 0.007% / 0.790% |
| 2025-11-14 11:00 | 3.78x | Full-bodied bearish | Impulse / continuation | -0.507% / -0.433% / -0.460% | True breakout | 66.7% | 12.1% | 21.2% | 1.79x | 0.622% / -0.007% |
| 2025-11-14 11:15 | 10.60x | Full-bodied bearish | Flat / fading | 0.075% / 0.136% / 0.109% | Weak move without breakout | 86.0% | 0.0% | 14.0% | 4.24x | 0.116% / 0.218% |
| 2025-11-14 15:00 | 3.27x | Bullish pin-bar / lower rejection | Flat / fading | -0.116% / -0.116% / -0.171% | Weak move without breakout | 25.5% | 13.7% | 60.8% | 2.12x | 0.314% / 0.177% |
| 2025-11-15 16:00 | 4.07x | Small-body bullish | Flat / fading | 0.000% / -0.007% / -0.021% | Weak move without breakout | 37.5% | 37.5% | 25.0% | 1.65x | 0.034% / 0.034% |
| 2025-11-15 17:45 | 3.34x | Bullish pin-bar / lower rejection | Reversal | -0.096% / -0.116% / -0.110% | Liquidity sweep / reversal | 10.0% | 0.0% | 90.0% | 3.94x | -0.007% / 0.144% |
| 2025-11-16 10:30 | 4.82x | Bullish pin-bar / lower rejection | Flat / fading | -0.014% / 0.048% / 0.027% | Position building in range | 45.8% | 8.3% | 45.8% | 2.73x | 0.048% / 0.055% |
| 2025-11-16 13:30 | 3.51x | Bearish pin-bar / upper rejection | Flat / fading | -0.041% / -0.014% / -0.021% | Position building in range | 43.7% | 56.3% | 0.0% | 1.61x | 0.021% / 0.048% |
| 2025-11-17 07:00 | 15.69x | Bullish pin-bar / lower rejection | Flat / fading | -0.014% / -0.130% / -0.048% | Weak move without breakout | 35.5% | 6.5% | 58.1% | 5.43x | 0.151% / 0.021% |
| 2025-11-17 07:15 | 7.16x | Bullish pin-bar / lower rejection | Flat / fading | -0.117% / -0.055% / -0.034% | Weak move without breakout | 9.1% | 13.6% | 77.3% | 2.88x | 0.137% / 0.007% |
| 2025-11-17 07:30 | 10.37x | Full-bodied bearish | Flat / fading | 0.062% / 0.082% / 0.027% | Position building in range | 85.7% | 0.0% | 14.3% | 2.37x | 0.021% / 0.103% |
| 2025-11-17 08:45 | 7.33x | Small-body bearish | Flat / fading | 0.028% / 0.062% / 0.069% | Weak move without breakout | 45.2% | 16.1% | 38.7% | 2.71x | 0.124% / 0.138% |
| 2025-11-17 09:00 | 3.76x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.034% / 0.055% / 0.302% | True breakout | 20.8% | 8.3% | 70.8% | 1.81x | 0.392% / 0.082% |
| 2025-11-17 10:00 | 7.80x | Small-body bullish | Impulse / continuation | -0.151% / 0.158% / 0.445% | True breakout | 53.6% | 18.8% | 27.5% | 4.18x | 0.829% / 0.233% |
| 2025-11-17 10:15 | 3.95x | Small-body bearish | Reversal | 0.309% / 0.528% / 0.487% | Liquidity sweep / reversal | 53.8% | 15.4% | 30.8% | 1.86x | 0.007% / 0.981% |
| 2025-11-17 10:30 | 4.30x | Full-bodied bullish | Impulse / continuation | 0.219% / 0.287% / 0.082% | True breakout | 71.7% | 23.3% | 5.0% | 2.54x | 0.671% / 0.014% |
| 2025-11-17 10:45 | 5.86x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.068% / -0.041% / -0.239% | False breakout | 52.5% | 47.5% | 0.0% | 2.29x | 0.451% / 0.280% |
| 2025-11-17 11:00 | 4.59x | Bearish pin-bar / upper rejection | Reversal | -0.109% / -0.205% / -0.184% | Liquidity sweep / reversal | 13.8% | 86.2% | 0.0% | 2.29x | 0.116% / 0.348% |
| 2025-11-18 07:00 | 9.21x | Bullish pin-bar / lower rejection | Reversal | 0.103% / 0.213% / -0.021% | Liquidity sweep / reversal | 17.4% | 28.3% | 54.3% | 3.19x | 0.083% / 0.330% |
| 2025-11-18 08:00 | 2.89x | Full-bodied bearish | Impulse / continuation | -0.151% / -0.186% / -0.110% | True breakout | 73.6% | 9.4% | 17.0% | 2.79x | 0.406% / 0.041% |
| 2025-11-18 08:15 | 7.90x | Bullish pin-bar / lower rejection | Flat / fading | -0.034% / -0.048% / 0.124% | Position building in range | 33.8% | 9.2% | 56.9% | 2.97x | 0.172% / 0.166% |
| 2025-11-18 10:15 | 17.43x | Full-bodied bullish | Impulse / continuation | 0.116% / -0.191% / 1.443% | True breakout | 65.9% | 22.9% | 11.2% | 7.89x | 1.491% / 0.470% |
| 2025-11-18 10:30 | 4.90x | Bearish pin-bar / upper rejection | Reversal | -0.306% / 0.476% / 1.339% | Liquidity sweep / reversal | 11.3% | 73.2% | 15.5% | 1.44x | 1.910% / 0.585% |
| 2025-11-18 11:00 | 4.42x | Full-bodied bullish | Impulse / continuation | 0.846% / 0.859% / 1.157% | True breakout | 67.6% | 8.2% | 24.1% | 3.14x | 1.428% / -0.014% |
| 2025-11-18 11:15 | 4.28x | Full-bodied bullish | Impulse / continuation | 0.013% / 0.215% / 0.248% | True breakout | 94.6% | 5.4% | 0.0% | 2.01x | 0.577% / 0.134% |
| 2025-11-18 11:30 | 3.43x | Bearish pin-bar / upper rejection | Reversal | 0.201% / 0.295% / -0.470% | Liquidity sweep / reversal | 1.9% | 79.2% | 18.9% | 1.46x | 0.530% / 0.590% |
| 2025-11-18 22:00 | 3.70x | Full-bodied bullish | Flat / fading | -0.174% / -0.194% / -0.234% | Position building in range | 76.6% | 20.3% | 3.1% | 4.09x | -0.027% / 0.314% |
| 2025-11-18 23:15 | 3.68x | Full-bodied bearish | Impulse -> reversal | -0.599% / -0.047% / 0.552% | False breakout | 79.3% | 9.2% | 11.5% | 4.32x | 0.733% / 0.733% |
| 2025-11-18 23:30 | 8.04x | Full-bodied bearish | Reversal | 0.555% / 0.738% / 1.306% | Liquidity sweep / reversal | 81.1% | 0.0% | 18.9% | 4.38x | -0.007% / 1.340% |
| 2025-11-19 07:00 | 3.96x | Full-bodied bullish | Impulse / continuation | 0.147% / 0.335% / 0.495% | True breakout | 62.6% | 29.7% | 7.7% | 2.42x | 0.736% / 0.007% |
| 2025-11-19 07:30 | 3.67x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.140% / 0.160% / 0.267% | True breakout | 37.3% | 57.3% | 5.3% | 1.70x | 0.653% / 0.073% |
| 2025-11-19 10:00 | 2.33x | Small-body bearish | Reversal | -0.067% / 0.527% / 0.634% | Liquidity sweep / reversal | 53.3% | 30.0% | 16.7% | 1.20x | 0.080% / 0.714% |
| 2025-11-19 10:30 | 2.31x | Full-bodied bullish | Impulse / continuation | -0.060% / 0.106% / -0.391% | True breakout | 91.5% | 3.2% | 5.3% | 1.92x | 0.504% / 0.544% |
| 2025-11-19 10:45 | 2.35x | Bearish pin-bar / upper rejection | Reversal | 0.166% / 0.385% / -0.119% | Liquidity sweep / reversal | 18.4% | 57.1% | 24.5% | 1.00x | 0.485% / 0.564% |
| 2025-11-19 11:30 | 4.36x | Full-bodied bearish | Impulse / continuation | 0.213% / 0.107% / -0.453% | True breakout | 68.4% | 17.1% | 14.6% | 3.21x | 0.606% / 0.340% |
| 2025-11-19 14:15 | 2.63x | Full-bodied bullish | Impulse / continuation | 0.225% / 0.722% / 1.423% | True breakout | 60.0% | 25.7% | 14.3% | 1.26x | 1.450% / 0.238% |
| 2025-11-19 14:45 | 2.93x | Small-body bullish | Impulse / continuation | 0.269% / 0.697% / 0.427% | True breakout | 57.6% | 22.0% | 20.5% | 2.27x | 0.749% / 0.026% |
| 2025-11-19 15:00 | 2.93x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.426% / 0.157% / 1.180% | True breakout | 41.4% | 54.5% | 4.0% | 1.54x | 1.304% / 0.249% |
| 2025-11-19 16:00 | 2.55x | Full-bodied bullish | Flat / fading | -0.194% / -0.408% / -0.272% | Weak move without breakout | 89.1% | 10.9% | 0.0% | 2.72x | 0.259% / 0.505% |
| 2025-11-20 10:00 | 21.38x | Small-body bullish | Reversal | -0.466% / -0.816% / -0.622% | Liquidity sweep / reversal | 53.8% | 33.3% | 12.8% | 3.67x | 0.019% / 0.939% |
| 2025-11-20 10:15 | 3.70x | Full-bodied bearish | Flat / fading | -0.351% / 0.104% / 0.059% | Weak move without breakout | 70.0% | 5.0% | 25.0% | 1.94x | 0.475% / 0.143% |
| 2025-11-20 20:45 | 14.51x | Full-bodied bullish | Flat / fading | 0.019% / -0.804% / -0.740% | Position building in range | 82.7% | 14.0% | 3.3% | 13.69x | 0.354% / 1.242% |
| 2025-11-20 21:00 | 5.25x | Bullish pin-bar / lower rejection | Reversal | -0.823% / -0.765% / -0.707% | Liquidity sweep / reversal | 8.8% | 41.6% | 49.6% | 2.36x | 0.006% / 1.261% |
| 2025-11-20 21:15 | 3.41x | Full-bodied bearish | Flat / fading | 0.058% / 0.065% / 0.331% | Weak move without breakout | 66.7% | 0.5% | 32.8% | 3.16x | 0.441% / 0.480% |
| 2025-11-21 15:15 | 5.61x | Bullish pin-bar / lower rejection | Flat / fading | 0.085% / -0.013% / -0.182% | Weak move without breakout | 36.7% | 16.0% | 47.3% | 4.56x | 0.338% / 0.312% |
| 2025-11-21 17:45 | 4.26x | Bearish pin-bar / upper rejection | Flat / fading | 0.032% / 0.090% / 0.090% | Position building in range | 44.2% | 55.8% | 0.0% | 2.34x | 0.284% / 0.149% |
| 2025-11-24 07:00 | 3.80x | Full-bodied bullish | Flat / fading | -0.160% / -0.236% / -0.243% | Position building in range | 85.6% | 5.2% | 9.3% | 3.03x | 0.032% / 0.345% |
| 2025-11-24 10:00 | 4.09x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.013% / -0.006% / -0.282% | True breakout | 22.5% | 49.3% | 28.2% | 2.10x | 0.449% / 0.353% |
| 2025-11-24 10:15 | 3.28x | Bearish pin-bar / upper rejection | Reversal | -0.019% / -0.340% / -0.263% | Liquidity sweep / reversal | 3.4% | 91.4% | 5.2% | 1.60x | 0.109% / 0.462% |
| 2025-11-24 10:45 | 2.92x | Full-bodied bearish | Impulse / continuation | 0.045% / 0.077% / -0.837% | True breakout | 84.7% | 5.1% | 10.2% | 2.14x | 1.081% / 0.161% |
| 2025-11-24 11:30 | 2.63x | Full-bodied bearish | Impulse / continuation | -0.581% / -0.368% / -0.568% | True breakout | 62.7% | 7.2% | 30.1% | 2.68x | 0.826% / 0.019% |
| 2025-11-24 11:45 | 3.30x | Full-bodied bearish | Flat / fading | 0.214% / 0.104% / 0.013% | Position building in range | 69.5% | 1.5% | 29.0% | 3.65x | 0.169% / 0.331% |
| 2025-11-24 17:15 | 2.57x | Small-body bearish | Flat / fading | -0.247% / -0.176% / -0.039% | Weak move without breakout | 57.7% | 8.5% | 33.8% | 1.86x | 0.377% / 0.319% |
| 2025-11-24 23:30 | 6.10x | Full-bodied bullish | Impulse / continuation | -0.065% / 0.117% / -0.039% | True breakout | 66.7% | 33.3% | 0.0% | 3.97x | 0.351% / 0.065% |
| 2025-11-25 07:00 | 3.15x | Bearish pin-bar / upper rejection | Reversal | -0.084% / -0.013% / 0.117% | Liquidity sweep / reversal | 34.0% | 60.0% | 6.0% | 3.10x | 0.104% / 0.208% |
| 2025-11-25 09:15 | 4.18x | Full-bodied bullish | Flat / fading | -0.006% / -0.175% / 0.032% | Weak move without breakout | 90.7% | 9.3% | 0.0% | 1.76x | 0.123% / 0.285% |
| 2025-11-25 10:00 | 2.51x | Doji | Impulse / continuation | 0.201% / 0.045% / -0.143% | True breakout | 0.0% | 51.4% | 48.6% | 1.43x | 0.344% / 0.344% |
| 2025-11-25 10:15 | 4.02x | Full-bodied bullish | Reversal | -0.155% / -0.123% / -0.240% | Liquidity sweep / reversal | 60.4% | 26.4% | 13.2% | 1.96x | 0.142% / 0.389% |
| 2025-11-25 11:30 | 4.19x | Small-body bearish | Impulse / continuation | -0.247% / -0.300% / -0.241% | True breakout | 52.3% | 14.8% | 33.0% | 2.79x | 0.586% / 0.098% |
| 2025-11-25 11:45 | 3.24x | Small-body bearish | Impulse / continuation | -0.052% / -0.098% / 0.176% | True breakout | 55.9% | 22.1% | 22.1% | 1.86x | 0.339% / 0.215% |
| 2025-11-25 12:00 | 3.24x | Bullish pin-bar / lower rejection | Reversal | -0.046% / 0.059% / 0.046% | Liquidity sweep / reversal | 16.9% | 8.5% | 74.6% | 1.46x | 0.144% / 0.268% |
| 2025-11-25 15:15 | 3.71x | Full-bodied bullish | Impulse / continuation | 0.479% / -0.246% / 0.045% | True breakout | 67.1% | 9.9% | 23.0% | 3.96x | 0.595% / 0.317% |
| 2025-11-25 15:30 | 5.83x | Small-body bullish | Reversal | -0.721% / -0.380% / -0.406% | Liquidity sweep / reversal | 55.0% | 6.1% | 38.9% | 2.95x | 0.116% / 0.766% |
| 2025-11-25 15:45 | 3.90x | Full-bodied bearish | Flat / fading | 0.344% / 0.292% / 0.454% | Weak move without breakout | 82.8% | 14.2% | 3.0% | 2.70x | 0.045% / 0.603% |
| 2025-11-26 10:30 | 3.28x | Full-bodied bullish | Flat / fading | 0.103% / 0.129% / -0.019% | Weak move without breakout | 78.4% | 21.6% | 0.0% | 1.65x | 0.206% / 0.084% |
| 2025-11-26 11:30 | 2.61x | Small-body bearish | Flat / fading | -0.039% / 0.123% / 0.064% | Weak move without breakout | 57.8% | 20.0% | 22.2% | 1.56x | 0.077% / 0.213% |
| 2025-11-27 07:00 | 3.05x | Full-bodied bearish | Flat / fading | -0.006% / 0.032% / 0.065% | Weak move without breakout | 64.3% | 33.3% | 2.4% | 4.39x | 0.045% / 0.129% |
| 2025-11-27 08:15 | 2.88x | Full-bodied bullish | Impulse / continuation | 0.006% / 0.090% / 0.084% | True breakout | 87.5% | 6.2% | 6.2% | 1.26x | 0.232% / 0.019% |
| 2025-11-27 09:00 | 3.02x | Bearish pin-bar / upper rejection | Reversal | -0.032% / 0.006% / -0.064% | Liquidity sweep / reversal | 20.0% | 72.0% | 8.0% | 1.67x | 0.110% / 0.110% |
| 2025-11-27 10:00 | 4.17x | Small-body bearish | Impulse / continuation | -0.045% / -0.135% / -0.161% | True breakout | 44.1% | 35.3% | 20.6% | 1.99x | 0.239% / 0.071% |
| 2025-11-27 10:30 | 4.42x | Small-body bearish | Impulse / continuation | -0.058% / -0.026% / -0.187% | True breakout | 32.6% | 30.2% | 37.2% | 2.20x | 0.291% / 0.103% |
| 2025-11-27 11:00 | 2.53x | Bearish pin-bar / upper rejection | Reversal | -0.078% / -0.161% / -0.291% | Liquidity sweep / reversal | 17.2% | 69.0% | 13.8% | 1.43x | 0.045% / 0.310% |
| 2025-11-27 13:00 | 3.34x | Bullish pin-bar / lower rejection | Reversal | 0.052% / 0.194% / 0.188% | Liquidity sweep / reversal | 52.7% | 3.6% | 43.6% | 2.09x | 0.032% / 0.233% |
| 2025-11-27 16:30 | 2.44x | Doji | Impulse / continuation | 0.006% / -0.809% / -1.624% | True breakout | 0.0% | 55.3% | 44.7% | 1.47x | 1.760% / 1.760% |
| 2025-11-27 17:00 | 7.51x | Full-bodied bearish | Impulse / continuation | -0.607% / -0.822% / -0.555% | True breakout | 90.6% | 2.9% | 6.5% | 5.67x | 0.959% / 0.059% |
| 2025-11-27 17:15 | 5.43x | Full-bodied bearish | Impulse / continuation | -0.217% / -0.007% / 0.164% | True breakout | 80.9% | 7.8% | 11.3% | 3.53x | 0.354% / 0.171% |
| 2025-11-27 17:30 | 2.82x | Small-body bearish | Reversal | 0.211% / 0.270% / 0.355% | Liquidity sweep / reversal | 54.1% | 11.5% | 34.4% | 1.53x | 0.066% / 0.493% |
| 2025-11-27 17:45 | 3.32x | Full-bodied bullish | Flat / fading | 0.059% / 0.171% / 0.269% | Weak move without breakout | 66.7% | 14.6% | 18.8% | 1.12x | 0.282% / 0.276% |
| 2025-11-28 07:00 | 3.56x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.020% / -0.157% | Liquidity sweep / reversal | 27.7% | 17.0% | 55.3% | 4.01x | 0.020% / 0.177% |
| 2025-11-28 09:30 | 4.36x | Small-body bullish | Impulse / continuation | -0.007% / -0.020% / 0.144% | True breakout | 58.7% | 34.8% | 6.5% | 2.62x | 0.229% / 0.092% |
| 2025-11-28 09:45 | 4.18x | Doji | Impulse / continuation | -0.013% / 0.039% / 0.124% | True breakout | 0.0% | 50.0% | 50.0% | 1.19x | 0.236% / 0.236% |
| 2025-11-28 10:00 | 3.69x | Bearish pin-bar / upper rejection | Reversal | 0.052% / 0.164% / -0.098% | Liquidity sweep / reversal | 4.0% | 52.0% | 44.0% | 1.22x | 0.190% / 0.249% |
| 2025-11-28 10:30 | 3.90x | Bearish pin-bar / upper rejection | Reversal | -0.026% / -0.261% / -0.170% | Liquidity sweep / reversal | 54.8% | 41.9% | 3.2% | 1.41x | 0.033% / 0.353% |
| 2025-11-28 11:00 | 2.58x | Full-bodied bearish | Flat / fading | 0.020% / 0.092% / -0.052% | Weak move without breakout | 72.5% | 0.0% | 27.5% | 2.40x | 0.164% / 0.197% |
| 2025-11-28 12:00 | 2.77x | Small-body bearish | Reversal | 0.184% / 0.203% / 0.465% | Liquidity sweep / reversal | 55.6% | 13.0% | 31.5% | 2.30x | 0.007% / 0.577% |
| 2025-11-28 12:45 | 4.07x | Bearish pin-bar / upper rejection | Flat / fading | 0.052% / 0.000% / 0.039% | Position building in range | 53.3% | 41.7% | 5.0% | 2.13x | 0.091% / 0.111% |
| 2025-11-28 16:00 | 6.01x | Small-body bullish | Flat / fading | -0.033% / 0.117% / 0.052% | Weak move without breakout | 60.0% | 28.9% | 11.1% | 3.77x | 0.202% / 0.143% |
| 2025-11-28 17:45 | 3.18x | Full-bodied bullish | Impulse / continuation | 0.375% / 0.990% / 0.692% | True breakout | 76.3% | 0.0% | 23.7% | 1.87x | 1.339% / 0.000% |
| 2025-11-28 18:00 | 3.63x | Full-bodied bullish | Impulse / continuation | 0.612% / 0.322% / 0.284% | True breakout | 71.6% | 28.4% | 0.0% | 2.39x | 0.960% / 0.045% |
| 2025-11-28 18:15 | 5.50x | Small-body bullish | Flat / fading | -0.288% / -0.295% / -0.404% | Position building in range | 59.6% | 34.6% | 5.8% | 3.99x | 0.064% / 0.519% |
| 2025-11-29 18:15 | 5.03x | Full-bodied bearish | Reversal | -0.006% / 0.019% / 0.083% | Liquidity sweep / reversal | 90.0% | 10.0% | 0.0% | 3.41x | 0.006% / 0.122% |
| 2025-11-30 11:00 | 3.50x | Full-bodied bullish | Impulse / continuation | 0.026% / 0.051% / 0.058% | True breakout | 100.0% | 0.0% | 0.0% | 4.48x | 0.179% / 0.038% |
| 2025-11-30 11:15 | 3.06x | Full-bodied bullish | Impulse / continuation | 0.026% / 0.038% / 0.038% | True breakout | 66.7% | 16.7% | 16.7% | 1.73x | 0.154% / 0.032% |
| 2025-11-30 11:30 | 4.27x | Bearish pin-bar / upper rejection | Flat / fading | 0.013% / 0.006% / -0.019% | Position building in range | 13.8% | 69.0% | 17.2% | 3.79x | 0.026% / 0.038% |
| 2025-11-30 17:30 | 2.60x | Full-bodied bullish | Flat / fading | 0.006% / 0.026% / 0.038% | Weak move without breakout | 60.0% | 26.7% | 13.3% | 2.02x | 0.038% / 0.045% |
| 2025-11-30 18:00 | 3.56x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.013% / 0.013% / 0.224% | True breakout | 27.3% | 0.0% | 72.7% | 1.36x | 0.224% / 0.064% |
| 2025-11-30 18:45 | 6.15x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.192% / 0.070% / 0.096% | True breakout | 8.0% | 52.0% | 40.0% | 2.61x | 0.319% / -0.026% |
| 2025-12-01 07:00 | 12.82x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.026% / 0.026% / -0.198% | True breakout | 43.5% | 41.3% | 15.2% | 3.58x | 0.230% / 0.172% |
| 2025-12-01 07:15 | 2.59x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.172% / -0.140% | Liquidity sweep / reversal | 21.9% | 71.9% | 6.2% | 2.11x | 0.013% / 0.262% |
| 2025-12-01 09:15 | 4.59x | Full-bodied bearish | Reversal | 0.103% / 0.282% / -0.109% | Liquidity sweep / reversal | 95.6% | 2.2% | 2.2% | 1.99x | 0.237% / 0.353% |
| 2025-12-01 10:00 | 3.23x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.333% / -0.346% / 0.038% | True breakout | 20.5% | 0.0% | 79.5% | 1.53x | 0.461% / 0.102% |
| 2025-12-01 10:15 | 4.35x | Full-bodied bearish | Reversal | -0.013% / 0.032% / 0.238% | Liquidity sweep / reversal | 61.5% | 12.8% | 25.6% | 2.59x | 0.109% / 0.443% |
| 2025-12-01 12:30 | 2.45x | Full-bodied bullish | Flat / fading | -0.216% / -0.248% / -0.235% | Position building in range | 63.2% | 17.9% | 18.9% | 2.13x | 0.038% / 0.439% |
| 2025-12-01 21:00 | 2.75x | Full-bodied bearish | Flat / fading | -0.006% / 0.045% / -0.006% | Position building in range | 62.5% | 0.0% | 37.5% | 3.01x | 0.038% / 0.096% |
| 2025-12-01 22:45 | 5.14x | Full-bodied bearish | Impulse / continuation | 0.096% / -0.077% / 0.141% | True breakout | 93.2% | 1.4% | 5.5% | 5.81x | 0.160% / 0.160% |
| 2025-12-01 23:00 | 4.47x | Bullish pin-bar / lower rejection | Reversal | -0.173% / -0.064% / 0.122% | Liquidity sweep / reversal | 28.0% | 20.0% | 52.0% | 3.03x | 0.122% / 0.224% |
| 2025-12-02 09:00 | 2.69x | Full-bodied bullish | Flat / fading | -0.045% / -0.102% / 0.096% | Weak move without breakout | 88.9% | 11.1% | 0.0% | 1.18x | 0.128% / 0.173% |
| 2025-12-02 10:00 | 3.26x | Bullish pin-bar / lower rejection | Reversal | -0.109% / -0.032% / -0.153% | Liquidity sweep / reversal | 46.8% | 10.6% | 42.6% | 3.07x | 0.019% / 0.185% |
| 2025-12-02 11:45 | 5.40x | Small-body bullish | Flat / fading | 0.064% / 0.070% / 0.147% | Weak move without breakout | 55.3% | 34.2% | 10.5% | 3.72x | 0.198% / 0.083% |
| 2025-12-02 13:00 | 2.90x | Full-bodied bullish | Flat / fading | -0.095% / -0.089% / 0.057% | Weak move without breakout | 62.5% | 28.1% | 9.4% | 1.20x | 0.140% / 0.191% |
| 2025-12-02 13:45 | 2.71x | Full-bodied bullish | Flat / fading | -0.051% / -0.064% / -0.146% | Weak move without breakout | 88.2% | 11.8% | 0.0% | 1.28x | 0.032% / 0.216% |
| 2025-12-02 14:00 | 2.29x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / 0.044% / -0.102% | Weak move without breakout | 45.5% | 13.6% | 40.9% | 0.81x | 0.165% / 0.070% |
| 2025-12-02 16:00 | 2.32x | Small-body bullish | Reversal | -0.146% / -0.165% / -0.190% | Liquidity sweep / reversal | 56.5% | 21.7% | 21.7% | 1.99x | 0.006% / 0.241% |
| 2025-12-02 18:00 | 5.45x | Small-body bearish | Flat / fading | 0.160% / 0.051% / 0.089% | Position building in range | 57.6% | 5.1% | 37.3% | 5.40x | 0.172% / 0.185% |
| 2025-12-02 23:30 | 2.71x | Small-body bearish | Impulse / continuation | -0.032% / -1.220% / -1.182% | True breakout | 57.4% | 4.4% | 38.2% | 3.00x | 1.604% / 0.038% |
| 2025-12-03 07:00 | 15.74x | Bullish pin-bar / lower rejection | Flat / fading | -0.090% / -0.039% / 0.213% | Weak move without breakout | 24.5% | 18.4% | 57.1% | 2.58x | 0.226% / 0.161% |
| 2025-12-03 10:00 | 2.93x | Full-bodied bearish | Impulse / continuation | -0.123% / -0.394% / -0.775% | True breakout | 63.8% | 2.1% | 34.0% | 1.12x | 0.794% / 0.071% |
| 2025-12-03 10:30 | 3.27x | Full-bodied bearish | Impulse / continuation | -0.006% / -0.382% / -0.045% | True breakout | 67.2% | 7.8% | 25.0% | 1.91x | 0.402% / 0.019% |
| 2025-12-03 11:00 | 2.77x | Full-bodied bearish | Reversal | 0.202% / 0.338% / 0.449% | Liquidity sweep / reversal | 95.0% | 0.0% | 5.0% | 1.99x | 0.013% / 0.488% |
| 2025-12-03 17:15 | 3.87x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.188% / 0.207% / 0.472% | True breakout | 54.8% | 45.2% | 0.0% | 2.10x | 0.504% / 0.019% |
| 2025-12-03 17:30 | 3.14x | Full-bodied bullish | Impulse / continuation | 0.019% / 0.026% / 0.368% | True breakout | 82.4% | 5.9% | 11.8% | 1.55x | 0.478% / 0.065% |
| 2025-12-03 18:15 | 3.07x | Full-bodied bullish | Impulse / continuation | 0.084% / 0.103% / 0.013% | True breakout | 81.6% | 10.2% | 8.2% | 2.10x | 0.193% / 0.219% |
| 2025-12-04 07:00 | 7.13x | Full-bodied bullish | Reversal | -0.019% / -0.109% / -0.308% | Liquidity sweep / reversal | 82.0% | 16.0% | 2.0% | 3.45x | 0.096% / 0.320% |
| 2025-12-04 07:45 | 5.91x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.154% / -0.071% / -0.019% | True breakout | 14.9% | 68.1% | 17.0% | 2.62x | 0.167% / 0.000% |
| 2025-12-04 09:00 | 2.99x | Full-bodied bullish | Flat / fading | -0.115% / -0.186% / -0.179% | Position building in range | 84.8% | 15.2% | 0.0% | 2.12x | 0.006% / 0.243% |
| 2025-12-04 10:00 | 3.84x | Small-body bearish | Reversal | 0.019% / 0.083% / 0.257% | Liquidity sweep / reversal | 40.7% | 22.2% | 37.0% | 1.04x | 0.064% / 0.276% |
| 2025-12-04 16:45 | 3.60x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.064% / -0.045% / -0.269% | True breakout | 32.4% | 0.0% | 67.6% | 2.20x | 0.269% / 0.019% |
| 2025-12-04 23:30 | 2.77x | Full-bodied bullish | Impulse / continuation | 0.064% / 0.160% / 0.141% | True breakout | 62.5% | 31.3% | 6.2% | 2.80x | 0.225% / 0.038% |
| 2025-12-05 07:00 | 6.39x | Bullish pin-bar / lower rejection | Reversal | 0.026% / 0.045% / 0.077% | Liquidity sweep / reversal | 17.1% | 24.4% | 58.5% | 5.68x | 0.026% / 0.096% |
| 2025-12-05 10:00 | 3.49x | Small-body bearish | Reversal | 0.423% / 0.679% / 0.672% | Liquidity sweep / reversal | 45.0% | 35.0% | 20.0% | 1.47x | 0.000% / 0.801% |
| 2025-12-05 10:15 | 14.38x | Full-bodied bullish | Impulse / continuation | 0.255% / 0.268% / 0.580% | True breakout | 77.4% | 21.4% | 1.2% | 5.94x | 0.670% / 0.057% |
| 2025-12-05 10:30 | 9.34x | Small-body bullish | Impulse / continuation | 0.013% / -0.006% / 0.254% | True breakout | 60.0% | 24.6% | 15.4% | 3.41x | 0.439% / 0.159% |
| 2025-12-05 10:45 | 3.02x | Bearish pin-bar / upper rejection | Reversal | -0.019% / 0.312% / 0.242% | Liquidity sweep / reversal | 10.0% | 65.0% | 25.0% | 0.96x | 0.426% / 0.172% |
| 2025-12-05 11:15 | 6.83x | Small-body bullish | Impulse / continuation | -0.070% / -0.070% / 0.342% | True breakout | 57.8% | 15.6% | 26.7% | 3.99x | 0.463% / 0.152% |
| 2025-12-05 12:15 | 3.44x | Full-bodied bullish | Impulse / continuation | 0.025% / 0.057% / -0.044% | True breakout | 69.4% | 22.4% | 8.2% | 2.56x | 0.385% / 0.177% |
| 2025-12-05 12:30 | 3.48x | Bearish pin-bar / upper rejection | Reversal | 0.032% / -0.126% / -0.057% | Liquidity sweep / reversal | 3.1% | 89.1% | 7.8% | 1.67x | 0.133% / 0.202% |
| 2025-12-08 07:00 | 8.13x | Full-bodied bullish | Impulse / continuation | -0.031% / 0.056% / 0.168% | True breakout | 92.8% | 0.9% | 6.3% | 7.03x | 0.174% / 0.261% |
| 2025-12-08 07:15 | 3.41x | Bullish pin-bar / lower rejection | Reversal | 0.087% / 0.081% / 0.174% | Liquidity sweep / reversal | 11.6% | 2.3% | 86.0% | 1.86x | 0.000% / 0.224% |
| 2025-12-08 07:30 | 3.29x | Bearish pin-bar / upper rejection | Flat / fading | -0.006% / 0.112% / -0.043% | Weak move without breakout | 42.4% | 57.6% | 0.0% | 1.29x | 0.137% / 0.075% |
| 2025-12-08 08:45 | 2.97x | Bearish pin-bar / upper rejection | Flat / fading | -0.167% / -0.192% / -0.105% | Weak move without breakout | 47.4% | 48.7% | 3.9% | 2.66x | 0.006% / 0.248% |
| 2025-12-08 10:30 | 3.17x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.068% / 0.316% / 0.143% | True breakout | 45.5% | 40.9% | 13.6% | 1.71x | 0.627% / 0.037% |
| 2025-12-08 11:00 | 3.64x | Bearish pin-bar / upper rejection | Reversal | 0.006% / -0.173% / -0.334% | Liquidity sweep / reversal | 43.3% | 55.6% | 1.1% | 2.64x | 0.037% / 0.427% |
| 2025-12-08 13:45 | 2.68x | Bullish pin-bar / lower rejection | Flat / fading | 0.050% / 0.050% / 0.056% | Position building in range | 47.3% | 3.2% | 49.5% | 2.91x | 0.075% / 0.261% |
| 2025-12-08 15:30 | 3.18x | Full-bodied bearish | Reversal | 0.094% / 0.344% / 0.225% | Liquidity sweep / reversal | 68.0% | 4.0% | 28.0% | 1.48x | 0.025% / 0.387% |
| 2025-12-08 17:15 | 2.76x | Full-bodied bearish | Flat / fading | 0.157% / 0.000% / 0.044% | Weak move without breakout | 78.6% | 1.2% | 20.2% | 2.11x | 0.119% / 0.244% |
| 2025-12-08 20:45 | 3.07x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.207% / -0.564% / -0.395% | True breakout | 41.8% | 46.8% | 11.4% | 2.72x | 0.620% / 0.050% |
| 2025-12-09 10:00 | 6.71x | Bullish pin-bar / lower rejection | Reversal | -0.107% / -0.232% / -0.088% | Liquidity sweep / reversal | 39.6% | 11.3% | 49.1% | 2.20x | 0.138% / 0.269% |
| 2025-12-09 10:15 | 3.45x | Bearish pin-bar / upper rejection | Flat / fading | -0.125% / -0.094% / 0.088% | Weak move without breakout | 38.5% | 61.5% | 0.0% | 1.45x | 0.163% / 0.125% |
| 2025-12-09 14:00 | 3.03x | Full-bodied bullish | Impulse / continuation | 0.262% / 0.499% / 0.424% | True breakout | 92.3% | 2.6% | 5.1% | 3.83x | 0.755% / 0.106% |
| 2025-12-09 14:15 | 6.64x | Small-body bullish | Impulse / continuation | 0.236% / 0.305% / 0.187% | True breakout | 50.6% | 27.2% | 22.2% | 3.58x | 0.492% / 0.012% |
| 2025-12-09 14:30 | 5.79x | Full-bodied bullish | Flat / fading | 0.068% / -0.074% / -0.118% | Weak move without breakout | 62.7% | 32.2% | 5.1% | 2.13x | 0.255% / 0.199% |
| 2025-12-09 22:00 | 12.61x | Bearish pin-bar / upper rejection | Flat / fading | 0.415% / 0.229% / 0.068% | Position building in range | 36.1% | 63.9% | 0.0% | 6.52x | 0.446% / 0.000% |
| 2025-12-09 22:15 | 4.30x | Full-bodied bullish | Reversal | -0.185% / -0.117% / -0.499% | Liquidity sweep / reversal | 94.4% | 5.6% | 0.0% | 2.67x | 0.031% / 0.573% |
| 2025-12-10 12:15 | 3.29x | Bearish pin-bar / upper rejection | Reversal | -0.123% / -0.173% / -0.333% | Liquidity sweep / reversal | 34.4% | 62.5% | 3.1% | 1.01x | 0.019% / 0.432% |
| 2025-12-10 17:00 | 3.12x | Bearish pin-bar / upper rejection | Reversal | -0.117% / -0.161% / -0.235% | Liquidity sweep / reversal | 35.6% | 62.2% | 2.2% | 3.07x | 0.056% / 0.420% |
| 2025-12-10 17:45 | 3.54x | Full-bodied bearish | Flat / fading | 0.130% / 0.168% / 0.025% | Position building in range | 62.3% | 20.8% | 17.0% | 2.99x | -0.006% / 0.180% |
| 2025-12-10 19:00 | 3.94x | Bearish pin-bar / upper rejection | Flat / fading | 0.062% / 0.050% / 0.142% | Position building in range | 27.8% | 44.3% | 27.8% | 3.76x | 0.155% / 0.025% |
| 2025-12-11 08:00 | 5.20x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.049% / 0.142% / 0.160% | True breakout | 44.0% | 56.0% | 0.0% | 2.23x | 0.241% / 0.068% |
| 2025-12-11 08:30 | 2.87x | Full-bodied bullish | Impulse / continuation | 0.068% / 0.018% / 0.191% | True breakout | 91.4% | 2.9% | 5.7% | 2.78x | 0.253% / 0.086% |
| 2025-12-11 09:00 | 2.83x | Bullish pin-bar / lower rejection | Reversal | 0.049% / 0.173% / 0.505% | Liquidity sweep / reversal | 11.1% | 25.9% | 63.0% | 1.77x | 0.037% / 0.542% |
| 2025-12-11 09:30 | 9.29x | Small-body bullish | Impulse / continuation | 0.203% / 0.332% / 0.141% | True breakout | 52.6% | 26.3% | 21.1% | 2.33x | 0.406% / 0.018% |
| 2025-12-11 09:45 | 6.14x | Bearish pin-bar / upper rejection | Flat / fading | 0.129% / 0.086% / -0.074% | Weak move without breakout | 47.6% | 42.9% | 9.5% | 3.43x | 0.203% / 0.104% |
| 2025-12-11 10:00 | 3.99x | Small-body bullish | Reversal | -0.043% / -0.190% / 0.037% | Liquidity sweep / reversal | 59.5% | 10.8% | 29.7% | 1.68x | 0.074% / 0.233% |
| 2025-12-11 10:15 | 3.54x | Bullish pin-bar / lower rejection | Reversal | -0.147% / -0.159% / -0.074% | Liquidity sweep / reversal | 15.9% | 27.3% | 56.8% | 1.85x | 0.190% / 0.270% |
| 2025-12-11 11:00 | 5.28x | Full-bodied bullish | Impulse / continuation | -0.153% / -0.025% / 0.153% | True breakout | 88.4% | 9.3% | 2.3% | 1.50x | 0.368% / 0.196% |
| 2025-12-11 11:15 | 2.67x | Bearish pin-bar / upper rejection | Reversal | 0.129% / 0.295% / 0.258% | Liquidity sweep / reversal | 44.4% | 44.4% | 11.1% | 2.02x | 0.018% / 0.522% |
| 2025-12-11 18:00 | 7.26x | Bullish pin-bar / lower rejection | Reversal | -0.337% / -0.288% / 0.883% | Liquidity sweep / reversal | 10.2% | 20.4% | 69.4% | 3.40x | 1.300% / 0.435% |
| 2025-12-11 19:00 | 10.09x | Full-bodied bullish | Flat / fading | -0.152% / -0.310% / -0.194% | Position building in range | 70.5% | 27.9% | 1.6% | 6.56x | 0.115% / 0.365% |
| 2025-12-12 11:00 | 2.51x | Bullish pin-bar / lower rejection | Reversal | 0.178% / -0.110% / -0.251% | Liquidity sweep / reversal | 29.4% | 20.6% | 50.0% | 1.31x | 0.404% / 0.288% |
| 2025-12-12 11:30 | 3.04x | Full-bodied bearish | Impulse / continuation | -0.196% / -0.141% / -0.049% | True breakout | 81.0% | 12.1% | 6.9% | 2.15x | 0.294% / 0.129% |
| 2025-12-12 11:45 | 4.16x | Small-body bearish | Flat / fading | 0.055% / 0.068% / 0.074% | Position building in range | 44.9% | 31.9% | 23.2% | 2.29x | 0.037% / 0.197% |
| 2025-12-12 13:15 | 2.93x | Bearish pin-bar / upper rejection | Flat / fading | -0.043% / -0.215% / -0.264% | Weak move without breakout | 9.7% | 69.4% | 20.8% | 2.08x | 0.288% / 0.135% |
| 2025-12-12 14:30 | 3.55x | Full-bodied bearish | Impulse / continuation | -0.105% / -0.148% / -0.093% | True breakout | 98.5% | 0.0% | 1.5% | 1.73x | 0.358% / 0.006% |
| 2025-12-12 14:45 | 3.24x | Bullish pin-bar / lower rejection | Flat / fading | -0.043% / 0.062% / -0.025% | Position building in range | 30.5% | 0.0% | 69.5% | 1.46x | 0.105% / 0.080% |
| 2025-12-12 21:45 | 4.22x | Full-bodied bearish | Flat / fading | -0.031% / 0.195% / 0.075% | Position building in range | 65.4% | 0.0% | 34.6% | 2.51x | 0.176% / 0.270% |
| 2025-12-13 17:45 | 2.68x | Full-bodied bullish | Impulse / continuation | -0.013% / -0.013% / 0.025% | True breakout | 60.0% | 40.0% | 0.0% | 0.76x | 0.156% / 0.125% |
| 2025-12-13 18:00 | 8.35x | Bearish pin-bar / upper rejection | Reversal | 0.000% / 0.050% / 0.038% | Liquidity sweep / reversal | 4.4% | 55.6% | 40.0% | 6.85x | 0.025% / 0.069% |
| 2025-12-14 11:15 | 3.45x | Full-bodied bearish | Impulse / continuation | 0.019% / -0.075% / -0.081% | True breakout | 84.6% | 7.7% | 7.7% | 2.32x | 0.169% / 0.075% |
| 2025-12-14 11:45 | 3.56x | Full-bodied bearish | Impulse / continuation | -0.063% / -0.006% / -0.138% | True breakout | 60.0% | 12.0% | 28.0% | 1.99x | 0.157% / 0.031% |
| 2025-12-15 06:45 | 3.29x | Doji | Impulse / continuation | -0.013% / 0.050% / 0.106% | True breakout | 0.0% | 0.0% | 0.0% | 0.00x | 0.200% / 0.200% |
| 2025-12-15 07:00 | 20.58x | Bearish pin-bar / upper rejection | Reversal | 0.063% / 0.138% / 0.150% | Liquidity sweep / reversal | 1.9% | 62.3% | 35.8% | 4.47x | 0.000% / 0.181% |
| 2025-12-15 07:15 | 3.66x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.075% / 0.056% / 0.306% | True breakout | 32.1% | 64.3% | 3.6% | 1.86x | 0.375% / 0.056% |
| 2025-12-15 08:15 | 6.78x | Full-bodied bullish | Impulse / continuation | 0.162% / 0.174% / 0.293% | True breakout | 75.0% | 22.9% | 2.1% | 2.55x | 0.424% / 0.093% |
| 2025-12-15 08:30 | 5.93x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.012% / 0.062% / -0.044% | True breakout | 57.5% | 42.5% | 0.0% | 1.82x | 0.261% / 0.255% |
| 2025-12-15 09:00 | 6.65x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.068% / -0.106% / -0.311% | False breakout | 15.1% | 3.8% | 81.1% | 2.16x | 0.199% / 0.379% |
| 2025-12-15 09:15 | 4.52x | Bearish pin-bar / upper rejection | Reversal | -0.174% / -0.155% / -0.298% | Liquidity sweep / reversal | 34.4% | 65.6% | 0.0% | 1.18x | 0.068% / 0.447% |
| 2025-12-15 09:30 | 3.22x | Bullish pin-bar / lower rejection | Flat / fading | 0.019% / -0.205% / -0.062% | Weak move without breakout | 40.0% | 15.7% | 44.3% | 2.41x | 0.274% / 0.087% |
| 2025-12-15 10:00 | 2.63x | Full-bodied bearish | Flat / fading | 0.081% / 0.143% / 0.031% | Position building in range | 66.0% | 13.2% | 20.8% | 1.55x | 0.031% / 0.200% |
| 2025-12-15 13:00 | 2.38x | Full-bodied bullish | Flat / fading | -0.050% / -0.105% / -0.006% | Weak move without breakout | 77.6% | 17.2% | 5.2% | 1.96x | 0.149% / 0.180% |
| 2025-12-15 14:30 | 2.85x | Bearish pin-bar / upper rejection | Flat / fading | 0.099% / 0.080% / 0.012% | Position building in range | 39.6% | 58.5% | 1.9% | 1.83x | 0.179% / 0.062% |
| 2025-12-15 15:45 | 2.36x | Full-bodied bearish | Impulse / continuation | -0.137% / -0.006% / 0.155% | True breakout | 69.7% | 1.3% | 28.9% | 2.56x | 0.348% / 0.168% |
| 2025-12-15 19:15 | 2.87x | Bearish pin-bar / upper rejection | Flat / fading | -0.099% / -0.210% / -0.025% | Weak move without breakout | 36.0% | 60.0% | 4.0% | 2.66x | 0.049% / 0.346% |
| 2025-12-16 07:15 | 3.95x | Bearish pin-bar / upper rejection | Reversal | -0.086% / -0.068% / -0.086% | Liquidity sweep / reversal | 33.3% | 62.7% | 3.9% | 2.41x | 0.037% / 0.178% |
| 2025-12-16 10:45 | 12.60x | Full-bodied bullish | Flat / fading | -0.134% / -0.220% / -0.024% | Weak move without breakout | 95.4% | 4.6% | 0.0% | 5.68x | 0.159% / 0.300% |
| 2025-12-16 11:00 | 3.93x | Bearish pin-bar / upper rejection | Flat / fading | -0.086% / -0.031% / 0.116% | Weak move without breakout | 33.9% | 47.5% | 18.6% | 2.05x | 0.165% / 0.129% |
| 2025-12-17 07:00 | 4.67x | Small-body bullish | Impulse / continuation | 0.012% / 0.055% / 0.067% | True breakout | 56.0% | 32.0% | 12.0% | 4.83x | 0.256% / 0.085% |
| 2025-12-17 07:45 | 2.54x | Small-body bullish | Reversal | -0.085% / -0.067% / -0.110% | Liquidity sweep / reversal | 48.3% | 37.9% | 13.8% | 2.07x | 0.104% / 0.116% |
| 2025-12-17 08:00 | 2.58x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.018% / 0.000% / -0.128% | True breakout | 42.9% | 45.7% | 11.4% | 2.26x | 0.244% / 0.037% |
| 2025-12-17 09:00 | 4.73x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.049% / -0.061% / -0.458% | True breakout | 47.2% | 0.0% | 52.8% | 2.10x | 0.544% / 0.061% |
| 2025-12-17 09:45 | 3.31x | Small-body bearish | Impulse / continuation | -0.330% / -0.575% / -0.465% | True breakout | 42.3% | 19.2% | 38.5% | 1.31x | 0.703% / 0.086% |
| 2025-12-17 10:00 | 7.24x | Full-bodied bearish | Impulse / continuation | -0.245% / -0.123% / 0.160% | True breakout | 64.6% | 18.3% | 17.1% | 4.00x | 0.374% / 0.221% |
| 2025-12-17 10:15 | 6.66x | Full-bodied bearish | Reversal | 0.123% / 0.111% / 0.197% | Liquidity sweep / reversal | 66.1% | 0.0% | 33.9% | 2.44x | 0.031% / 0.547% |
| 2025-12-17 12:00 | 3.87x | Full-bodied bearish | Impulse / continuation | 0.006% / -0.253% / -0.209% | True breakout | 66.7% | 1.7% | 31.7% | 1.72x | 0.425% / 0.062% |
| 2025-12-17 19:00 | 2.83x | Small-body bullish | Reversal | -0.049% / -0.068% / -0.179% | Liquidity sweep / reversal | 31.8% | 30.3% | 37.9% | 1.83x | 0.018% / 0.246% |
| 2025-12-18 07:00 | 4.70x | Bearish pin-bar / upper rejection | Reversal | -0.166% / -0.037% / -0.074% | Liquidity sweep / reversal | 30.0% | 63.3% | 6.7% | 2.49x | 0.012% / 0.221% |
| 2025-12-18 10:45 | 4.72x | Full-bodied bullish | Flat / fading | -0.074% / -0.086% / -0.123% | Weak move without breakout | 96.8% | 3.2% | 0.0% | 1.54x | 0.049% / 0.233% |
| 2025-12-18 11:00 | 2.68x | Small-body bearish | Impulse / continuation | -0.012% / -0.025% / -0.129% | True breakout | 54.2% | 29.2% | 16.7% | 1.21x | 0.203% / 0.061% |
| 2025-12-18 12:45 | 2.69x | Small-body bullish | Reversal | 0.000% / -0.080% / -0.074% | Liquidity sweep / reversal | 30.0% | 35.0% | 35.0% | 0.89x | 0.055% / 0.117% |
| 2025-12-18 15:00 | 2.39x | Full-bodied bullish | Flat / fading | 0.111% / -0.215% / -0.105% | Weak move without breakout | 71.8% | 16.9% | 11.3% | 2.77x | 0.117% / 0.295% |
| 2025-12-18 17:30 | 2.63x | Full-bodied bearish | Impulse / continuation | -0.155% / -0.261% / -0.056% | True breakout | 77.4% | 4.8% | 17.7% | 1.73x | 0.347% / 0.161% |
| 2025-12-18 18:15 | 2.05x | Bearish pin-bar / upper rejection | Reversal | 0.099% / -0.205% / 0.137% | Liquidity sweep / reversal | 25.8% | 59.7% | 14.5% | 1.58x | 0.242% / 0.211% |
| 2025-12-19 07:00 | 2.96x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.006% / -0.025% / -0.031% | True breakout | 30.0% | 62.5% | 7.5% | 2.21x | 0.142% / 0.062% |
| 2025-12-19 10:15 | 7.34x | Bearish pin-bar / upper rejection | Reversal | 0.111% / 0.129% / -0.062% | Liquidity sweep / reversal | 15.1% | 83.0% | 1.9% | 2.30x | 0.240% / 0.209% |
| 2025-12-19 11:00 | 3.21x | Bullish pin-bar / lower rejection | Flat / fading | -0.111% / -0.184% / 0.000% | Position building in range | 21.5% | 13.8% | 64.6% | 2.57x | 0.252% / 0.080% |
| 2025-12-19 13:15 | 4.56x | Full-bodied bullish | Reversal | -1.197% / -1.092% / -1.098% | Liquidity sweep / reversal | 71.8% | 25.4% | 2.8% | 1.92x | 0.018% / 2.301% |
| 2025-12-19 13:30 | 18.05x | Bullish pin-bar / lower rejection | Flat / fading | 0.106% / 0.286% / 0.174% | Position building in range | 51.6% | 0.8% | 47.6% | 9.30x | 0.460% / 0.385% |
| 2025-12-19 13:45 | 2.74x | Bullish pin-bar / lower rejection | Flat / fading | 0.180% / -0.006% / 0.310% | Weak move without breakout | 11.0% | 33.1% | 55.9% | 2.08x | 0.316% / 0.223% |
| 2025-12-21 10:00 | 3.53x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.031% / 0.000% / -0.013% | True breakout | 22.2% | 55.6% | 22.2% | 2.36x | 0.106% / 0.019% |
| 2025-12-21 10:15 | 3.30x | Bullish pin-bar / lower rejection | Flat / fading | 0.031% / 0.006% / 0.019% | Weak move without breakout | 27.8% | 5.6% | 66.7% | 2.14x | 0.038% / 0.050% |
| 2025-12-21 12:00 | 4.34x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.050% / -0.106% / -0.119% | True breakout | 20.0% | 0.0% | 80.0% | 1.21x | 0.200% / -0.006% |
| 2025-12-21 12:15 | 3.53x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.056% / -0.006% / -0.019% | True breakout | 33.3% | 0.0% | 66.7% | 2.53x | 0.150% / 0.000% |
| 2025-12-21 12:30 | 6.29x | Bullish pin-bar / lower rejection | Reversal | 0.050% / -0.013% / 0.031% | Liquidity sweep / reversal | 22.7% | 9.1% | 68.2% | 2.35x | 0.038% / 0.056% |
| 2025-12-21 16:45 | 3.37x | Full-bodied bearish | Flat / fading | 0.056% / 0.025% / 0.025% | Weak move without breakout | 70.6% | 17.6% | 11.8% | 2.45x | 0.019% / 0.082% |
| 2025-12-21 17:45 | 3.45x | Bearish pin-bar / upper rejection | Flat / fading | 0.038% / 0.038% / 0.069% | Weak move without breakout | 28.6% | 64.3% | 7.1% | 1.80x | 0.069% / -0.006% |
| 2025-12-22 07:00 | 23.42x | Doji / upper rejection | Flat / fading | -0.050% / 0.025% / 0.119% | Position building in range | 0.0% | 80.0% | 20.0% | 8.75x | 0.182% / 0.182% |
| 2025-12-22 08:00 | 2.74x | Bearish pin-bar / upper rejection | Reversal | 0.019% / -0.131% / -0.244% | Liquidity sweep / reversal | 52.4% | 47.6% | 0.0% | 1.50x | 0.038% / 0.394% |
| 2025-12-22 09:00 | 4.89x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.138% / -0.088% / -0.320% | True breakout | 38.5% | 0.0% | 61.5% | 2.49x | 0.533% / -0.006% |
| 2025-12-22 09:15 | 4.83x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.050% / 0.031% / -0.565% | True breakout | 47.7% | 0.0% | 52.3% | 2.51x | 0.760% / 0.119% |
| 2025-12-22 10:00 | 6.54x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.384% / -0.415% / -0.428% | True breakout | 48.5% | 1.5% | 50.0% | 3.04x | 0.623% / 0.050% |
| 2025-12-22 10:15 | 7.49x | Full-bodied bearish | Flat / fading | -0.032% / -0.107% / -0.013% | Weak move without breakout | 62.0% | 7.0% | 31.0% | 3.73x | 0.240% / 0.095% |
| 2025-12-22 10:30 | 3.04x | Bullish pin-bar / lower rejection | Reversal | -0.076% / -0.013% / 0.051% | Liquidity sweep / reversal | 15.0% | 35.0% | 50.0% | 1.19x | 0.208% / 0.114% |
| 2025-12-22 12:45 | 3.04x | Bearish pin-bar / upper rejection | Reversal | -0.069% / -0.019% / 0.000% | Liquidity sweep / reversal | 22.2% | 48.1% | 29.6% | 1.49x | 0.069% / 0.126% |
| 2025-12-22 21:15 | 2.82x | Full-bodied bearish | Impulse / continuation | 0.070% / 0.038% / -0.330% | True breakout | 73.6% | 0.0% | 26.4% | 4.24x | 0.418% / 0.095% |
| 2025-12-22 22:00 | 4.36x | Full-bodied bearish | Flat / fading | -0.025% / 0.045% / 0.013% | Position building in range | 75.7% | 0.0% | 24.3% | 4.82x | 0.083% / 0.089% |
| 2025-12-23 07:00 | 2.91x | Bearish pin-bar / upper rejection | Flat / fading | 0.095% / -0.013% / 0.000% | Position building in range | 32.4% | 43.2% | 24.3% | 1.74x | 0.095% / 0.044% |
| 2025-12-23 10:15 | 5.13x | Small-body bullish | Impulse / continuation | 0.349% / 0.375% / 0.280% | True breakout | 42.6% | 38.3% | 19.1% | 2.17x | 0.572% / 0.070% |
| 2025-12-23 10:30 | 10.47x | Full-bodied bullish | Flat / fading | 0.025% / 0.209% / -0.241% | Weak move without breakout | 69.6% | 16.5% | 13.9% | 3.21x | 0.222% / 0.418% |
| 2025-12-23 10:45 | 2.92x | Bearish pin-bar / upper rejection | Reversal | 0.184% / -0.095% / -0.234% | Liquidity sweep / reversal | 12.0% | 64.0% | 24.0% | 0.90x | 0.196% / 0.443% |
| 2025-12-23 14:45 | 2.99x | Full-bodied bullish | Flat / fading | -0.082% / -0.183% / -0.208% | Weak move without breakout | 76.5% | 22.2% | 1.2% | 2.86x | 0.038% / 0.417% |
| 2025-12-24 07:00 | 3.76x | Small-body bearish | Impulse / continuation | -0.151% / -0.038% / -0.126% | True breakout | 40.6% | 37.5% | 21.9% | 2.48x | 0.164% / 0.038% |
| 2025-12-24 10:00 | 4.77x | Doji / lower rejection | Impulse / continuation | 0.000% / -0.095% / -0.227% | True breakout | 0.0% | 22.0% | 78.0% | 2.10x | 0.366% / 0.366% |
| 2025-12-24 10:15 | 2.59x | Bullish pin-bar / lower rejection | Reversal | -0.095% / -0.107% / -0.480% | Liquidity sweep / reversal | 7.3% | 26.8% | 65.9% | 1.97x | 0.107% / 0.512% |
| 2025-12-24 11:00 | 4.01x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.253% / -0.063% / -0.019% | True breakout | 24.0% | 46.7% | 29.3% | 3.62x | 0.298% / 0.165% |
| 2025-12-24 11:15 | 3.26x | Full-bodied bearish | Flat / fading | 0.190% / 0.190% / 0.159% | Weak move without breakout | 76.5% | 13.7% | 9.8% | 2.08x | 0.044% / 0.419% |
| 2025-12-24 11:30 | 3.26x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / 0.044% / 0.070% | Position building in range | 42.5% | 49.3% | 8.2% | 2.70x | 0.095% / 0.165% |
| 2025-12-24 14:15 | 2.54x | Bearish pin-bar / upper rejection | Flat / fading | -0.019% / -0.038% / 0.013% | Position building in range | 37.5% | 55.0% | 7.5% | 1.16x | 0.126% / 0.082% |
| 2025-12-24 15:30 | 2.04x | Bearish pin-bar / upper rejection | Flat / fading | 0.070% / -0.019% / 0.025% | Weak move without breakout | 34.7% | 61.2% | 4.1% | 1.88x | 0.070% / 0.095% |
| 2025-12-25 09:30 | 8.91x | Bullish pin-bar / lower rejection | Flat / fading | 0.070% / -0.032% / 0.000% | Weak move without breakout | 53.0% | 3.0% | 43.9% | 6.20x | 0.210% / 0.133% |
| 2025-12-25 10:00 | 3.73x | Small-body bearish | Impulse -> reversal | -0.013% / 0.032% / 0.438% | False breakout | 55.2% | 10.3% | 34.5% | 1.85x | 0.178% / 0.508% |
| 2025-12-25 10:15 | 4.98x | Bearish pin-bar / upper rejection | Reversal | 0.044% / 0.216% / 0.585% | Liquidity sweep / reversal | 5.6% | 61.1% | 33.3% | 1.05x | 0.165% / 0.667% |
| 2025-12-25 10:30 | 7.28x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.172% / 0.407% / 0.673% | True breakout | 19.4% | 8.3% | 72.2% | 2.06x | 0.680% / 0.025% |
| 2025-12-25 10:45 | 3.17x | Full-bodied bullish | Impulse / continuation | 0.235% / 0.368% / 0.564% | True breakout | 84.4% | 3.1% | 12.5% | 1.74x | 0.609% / 0.057% |
| 2025-12-25 11:00 | 3.97x | Full-bodied bullish | Impulse / continuation | 0.133% / 0.266% / 0.304% | True breakout | 64.9% | 19.3% | 15.8% | 2.91x | 0.373% / 0.000% |
| 2025-12-25 11:15 | 4.38x | Full-bodied bullish | Impulse / continuation | 0.133% / 0.196% / 0.278% | True breakout | 61.8% | 38.2% | 0.0% | 1.47x | 0.366% / 0.019% |
| 2025-12-25 19:00 | 3.01x | Bearish pin-bar / upper rejection | Flat / fading | 0.013% / 0.139% / 0.063% | Weak move without breakout | 4.4% | 55.6% | 40.0% | 2.32x | 0.246% / 0.013% |
| 2025-12-25 22:00 | 3.38x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.032% / -0.013% / 0.013% | True breakout | 5.7% | 82.9% | 11.4% | 2.47x | 0.120% / 0.063% |
| 2025-12-26 08:00 | 2.82x | Small-body bearish | Reversal | 0.063% / -0.019% / 0.145% | Liquidity sweep / reversal | 54.2% | 33.3% | 12.5% | 1.33x | 0.050% / 0.233% |
| 2025-12-26 09:00 | 4.48x | Small-body bullish | Impulse / continuation | 0.315% / 0.630% / 0.813% | True breakout | 55.6% | 31.1% | 13.3% | 2.66x | 1.071% / 0.050% |
| 2025-12-26 09:15 | 6.52x | Full-bodied bullish | Impulse / continuation | 0.314% / 0.471% / 0.540% | True breakout | 79.4% | 7.9% | 12.7% | 3.27x | 0.754% / 0.019% |
| 2025-12-26 09:30 | 7.27x | Full-bodied bullish | Impulse / continuation | 0.157% / 0.182% / 0.213% | True breakout | 82.5% | 15.9% | 1.6% | 2.73x | 0.438% / 0.031% |
| 2025-12-26 09:45 | 8.96x | Bearish pin-bar / upper rejection | Flat / fading | 0.025% / 0.069% / 0.188% | Position building in range | 37.3% | 60.0% | 2.7% | 2.88x | 0.250% / 0.006% |
| 2025-12-26 10:00 | 3.05x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.044% / 0.031% / 0.319% | True breakout | 12.2% | 87.8% | 0.0% | 1.34x | 0.425% / 0.025% |
| 2025-12-26 11:00 | 2.73x | Bearish pin-bar / upper rejection | Reversal | -0.062% / -0.143% / -0.280% | Liquidity sweep / reversal | 59.5% | 40.5% | 0.0% | 1.26x | 0.025% / 0.280% |
| 2025-12-26 23:15 | 4.65x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.025% / -0.018% / 0.326% | True breakout | 38.7% | 56.5% | 4.8% | 3.89x | 0.357% / 0.074% |
| 2025-12-28 10:00 | 5.29x | Small-body bearish | Impulse / continuation | -0.006% / -0.253% / -0.160% | True breakout | 59.5% | 35.1% | 5.4% | 7.51x | 0.394% / 0.117% |
| 2025-12-28 10:15 | 2.93x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.246% / -0.271% / -0.129% | True breakout | 4.2% | 79.2% | 16.7% | 3.26x | 0.388% / 0.000% |
| 2025-12-28 10:30 | 4.68x | Full-bodied bearish | Impulse / continuation | -0.025% / 0.093% / 0.117% | True breakout | 100.0% | 0.0% | 0.0% | 4.59x | 0.142% / 0.191% |
| 2025-12-28 10:45 | 4.90x | Bullish pin-bar / lower rejection | Reversal | 0.117% / 0.142% / 0.074% | Liquidity sweep / reversal | 26.5% | 17.6% | 55.9% | 2.97x | 0.000% / 0.216% |
| 2025-12-28 17:30 | 3.59x | Doji / lower rejection | Flat / fading | -0.074% / -0.111% / 0.025% | Weak move without breakout | 0.0% | 26.3% | 73.7% | 1.67x | 0.142% / 0.142% |
| 2025-12-28 18:00 | 2.78x | Small-body bearish | Reversal | 0.105% / 0.136% / 0.358% | Liquidity sweep / reversal | 30.8% | 30.8% | 38.5% | 1.10x | 0.000% / 0.358% |
| 2025-12-29 07:00 | 23.74x | Full-bodied bearish | Impulse / continuation | 0.080% / 0.142% / 0.154% | True breakout | 86.5% | 7.7% | 5.8% | 7.91x | 0.161% / 0.297% |
| 2025-12-29 07:15 | 4.74x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.062% / 0.111% / 0.167% | True breakout | 28.9% | 13.3% | 57.8% | 2.24x | 0.216% / 0.019% |
| 2025-12-29 11:00 | 2.65x | Full-bodied bullish | Impulse / continuation | 0.061% / 0.362% / 1.314% | True breakout | 85.1% | 8.5% | 6.4% | 1.58x | 2.032% / 0.098% |
| 2025-12-29 11:30 | 3.38x | Full-bodied bullish | Impulse / continuation | 1.321% / 0.948% / 0.826% | True breakout | 90.9% | 0.0% | 9.1% | 1.76x | 1.664% / 0.024% |
| 2025-12-29 11:45 | 9.11x | Full-bodied bullish | Impulse / continuation | -0.368% / -0.235% / -0.380% | True breakout | 98.7% | 1.3% | 0.0% | 6.61x | 0.338% / 0.694% |
| 2025-12-29 12:00 | 5.92x | Bearish pin-bar / upper rejection | Flat / fading | 0.133% / -0.121% / 0.061% | Weak move without breakout | 43.6% | 40.0% | 16.4% | 2.91x | 0.327% / 0.176% |
| 2025-12-29 18:00 | 2.56x | Full-bodied bearish | Flat / fading | -0.012% / -0.195% / -0.329% | Weak move without breakout | 82.2% | 0.5% | 17.3% | 3.67x | 0.372% / 0.469% |
| 2025-12-29 18:15 | 2.98x | Doji / upper rejection | Impulse / continuation | -0.183% / -0.250% / -0.201% | True breakout | 0.0% | 75.2% | 24.8% | 1.56x | 0.768% / 0.768% |
| 2025-12-30 07:00 | 4.26x | Full-bodied bullish | Flat / fading | -0.140% / -0.146% / -0.097% | Position building in range | 79.3% | 13.6% | 7.1% | 5.33x | 0.024% / 0.346% |
| 2025-12-30 11:00 | 2.79x | Full-bodied bearish | Flat / fading | -0.153% / -0.086% / 0.000% | Weak move without breakout | 81.1% | 0.0% | 18.9% | 1.55x | 0.221% / 0.123% |
| 2025-12-30 12:30 | 2.62x | Bullish pin-bar / lower rejection | Reversal | 0.031% / 0.031% / 0.006% | Liquidity sweep / reversal | 8.7% | 26.1% | 65.2% | 0.61x | 0.049% / 0.080% |
| 2025-12-30 13:45 | 3.32x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.074% / 0.110% / 0.337% | True breakout | 18.8% | 18.7% | 62.5% | 0.56x | 0.368% / 0.037% |
| 2025-12-30 23:15 | 3.39x | Small-body bearish | Reversal | 0.183% / 0.214% / 0.018% | Liquidity sweep / reversal | 57.6% | 24.2% | 18.2% | 2.52x | 0.092% / 0.312% |
| 2026-01-05 07:00 | 4.80x | Full-bodied bearish | Impulse / continuation | -0.141% / -0.250% / -0.189% | True breakout | 66.7% | 0.0% | 33.3% | 3.30x | 0.336% / 0.012% |
| 2026-01-05 09:00 | 2.93x | Small-body bearish | Flat / fading | -0.074% / -0.074% / -0.147% | Weak move without breakout | 57.1% | 4.3% | 38.6% | 2.71x | 0.288% / 0.043% |
| 2026-01-05 10:00 | 2.53x | Bullish pin-bar / lower rejection | Flat / fading | 0.006% / -0.184% / -0.018% | Weak move without breakout | 22.7% | 25.0% | 52.3% | 1.54x | 0.233% / 0.061% |
| 2026-01-05 10:45 | 2.37x | Bearish pin-bar / upper rejection | Flat / fading | 0.031% / 0.031% / 0.209% | Weak move without breakout | 50.0% | 40.9% | 9.1% | 1.48x | 0.209% / 0.061% |
| 2026-01-05 16:00 | 3.30x | Full-bodied bullish | Flat / fading | 0.018% / 0.055% / 0.043% | Weak move without breakout | 60.0% | 37.5% | 2.5% | 2.64x | 0.177% / 0.024% |
| 2026-01-05 17:00 | 2.72x | Bearish pin-bar / upper rejection | Reversal | 0.031% / -0.061% / 0.079% | Liquidity sweep / reversal | 26.1% | 69.6% | 4.3% | 1.42x | 0.079% / 0.116% |
| 2026-01-05 23:45 | 2.51x | Full-bodied bearish | Reversal | 0.208% / 0.410% / 0.386% | Liquidity sweep / reversal | 75.0% | 3.1% | 21.9% | 3.27x | -0.141% / 0.447% |
| 2026-01-06 07:00 | 3.52x | Full-bodied bullish | Flat / fading | -0.012% / -0.024% / -0.049% | Position building in range | 66.0% | 12.0% | 22.0% | 4.09x | 0.024% / 0.165% |
| 2026-01-06 09:15 | 2.78x | Full-bodied bullish | Impulse / continuation | 0.146% / 0.244% / 0.396% | True breakout | 89.5% | 5.3% | 5.3% | 1.05x | 0.506% / 0.012% |
| 2026-01-06 09:30 | 5.01x | Full-bodied bullish | Impulse / continuation | 0.097% / 0.024% / 0.317% | True breakout | 64.9% | 29.7% | 5.4% | 1.93x | 0.384% / 0.061% |
| 2026-01-06 09:45 | 2.73x | Full-bodied bullish | Impulse / continuation | -0.073% / 0.152% / 0.219% | True breakout | 70.8% | 29.2% | 0.0% | 1.12x | 0.335% / 0.158% |
| 2026-01-06 10:00 | 3.47x | Bullish pin-bar / lower rejection | Reversal | 0.225% / 0.292% / 0.304% | Liquidity sweep / reversal | 42.3% | 3.8% | 53.8% | 1.15x | 0.037% / 0.408% |
| 2026-01-06 10:15 | 5.24x | Small-body bullish | Flat / fading | 0.067% / 0.067% / 0.067% | Weak move without breakout | 57.4% | 29.5% | 13.1% | 2.75x | 0.182% / 0.024% |
| 2026-01-06 11:45 | 4.67x | Full-bodied bullish | Reversal | -0.188% / -0.278% / -0.315% | Liquidity sweep / reversal | 78.7% | 21.3% | 0.0% | 2.74x | 0.061% / 0.321% |
| 2026-01-06 17:45 | 2.60x | Full-bodied bearish | Reversal | 0.061% / 0.067% / 0.207% | Liquidity sweep / reversal | 84.0% | 4.0% | 12.0% | 1.49x | 0.006% / 0.207% |
| 2026-01-06 22:45 | 3.20x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.085% / 0.085% / 0.261% | True breakout | 48.5% | 51.5% | 0.0% | 2.61x | 0.261% / -0.006% |
| 2026-01-06 23:00 | 2.72x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.000% / 0.097% / -0.977% | False breakout | 50.0% | 50.0% | 0.0% | 1.85x | 0.176% / 0.977% |
| 2026-01-06 23:30 | 3.09x | Full-bodied bullish | Reversal | 0.079% / -1.073% / -1.321% | Liquidity sweep / reversal | 88.9% | 11.1% | 0.0% | 1.17x | 0.079% / 1.437% |
| 2026-01-06 23:45 | 2.86x | Bullish pin-bar / lower rejection | Reversal | -1.151% / -1.339% / -1.478% | Liquidity sweep / reversal | 55.0% | 0.0% | 45.0% | 1.23x | -1.145% / 1.514% |
| 2026-01-08 10:00 | 9.99x | Bullish pin-bar / lower rejection | Flat / fading | -0.061% / -0.141% / -0.221% | Weak move without breakout | 50.8% | 1.6% | 47.5% | 2.17x | 0.295% / 0.049% |
| 2026-01-08 20:30 | 3.52x | Bullish pin-bar / lower rejection | Reversal | -0.049% / -0.031% / 0.019% | Liquidity sweep / reversal | 4.5% | 0.0% | 95.5% | 1.96x | 0.099% / 0.093% |
| 2026-01-09 07:00 | 6.45x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.117% / 0.402% / 0.352% | True breakout | 5.3% | 12.7% | 82.0% | 12.73x | 0.581% / 0.062% |
| 2026-01-09 07:30 | 3.14x | Full-bodied bullish | Flat / fading | -0.068% / -0.049% / 0.080% | Weak move without breakout | 71.6% | 22.4% | 6.0% | 2.93x | 0.178% / 0.123% |
| 2026-01-09 14:00 | 4.15x | Small-body bullish | Impulse / continuation | 0.068% / 0.049% / 0.031% | True breakout | 45.5% | 27.3% | 27.3% | 1.71x | 0.135% / 0.006% |
| 2026-01-09 23:30 | 2.97x | Bearish pin-bar / upper rejection | Reversal | 0.093% / 0.012% / 0.383% | Liquidity sweep / reversal | 47.8% | 47.8% | 4.3% | 3.19x | 0.068% / 0.544% |
| 2026-01-12 07:00 | 16.82x | Full-bodied bullish | Flat / fading | -0.012% / -0.148% / -0.185% | Position building in range | 69.7% | 24.2% | 6.1% | 11.65x | 0.031% / 0.258% |
| 2026-01-12 07:15 | 2.59x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.135% / -0.135% / -0.166% | True breakout | 10.5% | 26.3% | 63.2% | 1.27x | 0.246% / 0.000% |
| 2026-01-12 09:30 | 3.03x | Full-bodied bullish | Impulse / continuation | -0.006% / 0.178% / 0.117% | True breakout | 92.1% | 7.9% | 0.0% | 1.62x | 0.301% / 0.111% |
| 2026-01-12 10:00 | 6.20x | Small-body bullish | Reversal | -0.227% / -0.061% / -0.012% | Liquidity sweep / reversal | 56.1% | 35.1% | 8.8% | 2.22x | 0.098% / 0.282% |
| 2026-01-12 14:00 | 5.42x | Full-bodied bearish | Impulse / continuation | -0.117% / -0.130% / -0.111% | True breakout | 86.5% | 8.1% | 5.4% | 3.21x | 0.192% / 0.012% |
| 2026-01-12 14:15 | 2.79x | Small-body bearish | Flat / fading | -0.012% / -0.043% / -0.006% | Weak move without breakout | 59.4% | 6.2% | 34.4% | 1.27x | 0.074% / 0.105% |
| 2026-01-13 07:00 | 5.53x | Full-bodied bullish | Flat / fading | -0.136% / -0.037% / -0.043% | Position building in range | 77.1% | 10.4% | 12.5% | 4.94x | 0.000% / 0.197% |
| 2026-01-13 09:30 | 2.61x | Full-bodied bearish | Impulse / continuation | -0.019% / -0.167% / -0.050% | True breakout | 60.0% | 17.5% | 22.5% | 2.20x | 0.173% / 0.124% |
| 2026-01-13 09:45 | 2.75x | Bullish pin-bar / lower rejection | Reversal | -0.149% / 0.019% / -0.136% | Liquidity sweep / reversal | 7.1% | 32.1% | 60.7% | 1.37x | 0.155% / 0.142% |
| 2026-01-13 10:15 | 2.54x | Bearish pin-bar / upper rejection | Reversal | -0.050% / -0.155% / -0.309% | Liquidity sweep / reversal | 58.3% | 41.7% | 0.0% | 2.08x | 0.056% / 0.328% |
| 2026-01-13 11:30 | 2.79x | Bullish pin-bar / lower rejection | Reversal | -0.043% / 0.043% / 0.087% | Liquidity sweep / reversal | 34.8% | 13.0% | 52.2% | 0.94x | 0.099% / 0.155% |
| 2026-01-13 16:15 | 2.93x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.019% / -0.161% / -0.453% | True breakout | 7.1% | 50.0% | 42.9% | 2.63x | 0.558% / 0.087% |
| 2026-01-13 17:00 | 5.37x | Bullish pin-bar / lower rejection | Flat / fading | -0.131% / -0.143% / -0.180% | Position building in range | 40.3% | 3.0% | 56.7% | 3.29x | 0.230% / 0.056% |
| 2026-01-13 18:15 | 2.96x | Full-bodied bearish | Impulse / continuation | -0.062% / -0.037% / -0.119% | True breakout | 79.1% | 4.7% | 16.3% | 1.69x | 0.237% / 0.012% |
| 2026-01-13 18:30 | 2.94x | Bullish pin-bar / lower rejection | Flat / fading | 0.025% / -0.044% / -0.063% | Weak move without breakout | 34.5% | 6.9% | 58.6% | 1.05x | 0.175% / 0.038% |
| 2026-01-14 07:00 | 3.42x | Bullish pin-bar / lower rejection | Reversal | -0.050% / -0.081% / -0.169% | Liquidity sweep / reversal | 2.5% | 32.5% | 65.0% | 3.11x | 0.056% / 0.225% |
| 2026-01-14 09:00 | 3.66x | Small-body bearish | Flat / fading | 0.100% / 0.025% / 0.031% | Weak move without breakout | 51.0% | 32.7% | 16.3% | 2.63x | 0.125% / 0.113% |
| 2026-01-14 09:45 | 2.99x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.013% / 0.094% / 0.132% | True breakout | 12.5% | 16.7% | 70.8% | 1.06x | 0.263% / 0.169% |
| 2026-01-14 10:00 | 3.73x | Bullish pin-bar / lower rejection | Reversal | 0.107% / 0.063% / 0.220% | Liquidity sweep / reversal | 6.5% | 12.9% | 80.6% | 1.33x | 0.019% / 0.276% |
| 2026-01-14 10:15 | 5.94x | Bearish pin-bar / upper rejection | Flat / fading | -0.044% / 0.038% / 0.263% | Weak move without breakout | 37.0% | 58.7% | 4.3% | 1.86x | 0.288% / 0.125% |
| 2026-01-14 10:30 | 3.07x | Bearish pin-bar / upper rejection | Reversal | 0.081% / 0.157% / 0.539% | Liquidity sweep / reversal | 14.7% | 47.1% | 38.2% | 1.29x | 0.031% / 1.122% |
| 2026-01-14 11:30 | 10.13x | Bearish pin-bar / upper rejection | Flat / fading | 0.262% / 0.075% / 0.274% | Position building in range | 27.7% | 71.5% | 0.8% | 4.60x | 0.374% / 0.006% |
| 2026-01-14 17:00 | 3.54x | Bearish pin-bar / upper rejection | Reversal | 0.044% / -0.031% / -0.149% | Liquidity sweep / reversal | 56.8% | 40.9% | 2.3% | 2.00x | 0.081% / 0.224% |
| 2026-01-14 19:00 | 6.24x | Bullish pin-bar / lower rejection | Flat / fading | -0.119% / -0.119% / -0.119% | Weak move without breakout | 48.1% | 0.0% | 51.9% | 2.34x | 0.200% / 0.012% |
| 2026-01-15 07:00 | 5.27x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.050% / 0.006% / -0.069% | True breakout | 58.8% | 0.0% | 41.2% | 4.49x | 0.106% / 0.087% |
| 2026-01-15 10:00 | 2.99x | Full-bodied bearish | Impulse / continuation | 0.031% / -0.037% / 0.050% | True breakout | 74.4% | 4.7% | 20.9% | 2.04x | 0.206% / 0.144% |
| 2026-01-15 10:30 | 3.26x | Bullish pin-bar / lower rejection | Reversal | -0.137% / 0.087% / 0.025% | Liquidity sweep / reversal | 34.4% | 0.0% | 65.6% | 1.35x | 0.169% / 0.181% |
| 2026-01-15 11:00 | 2.64x | Full-bodied bullish | Flat / fading | -0.025% / -0.062% / -0.131% | Position building in range | 70.4% | 27.8% | 1.9% | 2.42x | 0.075% / 0.225% |
| 2026-01-15 12:45 | 3.09x | Bearish pin-bar / upper rejection | Reversal | 0.407% / 0.326% / 0.288% | Liquidity sweep / reversal | 52.2% | 43.5% | 4.3% | 1.86x | 0.006% / 0.419% |
| 2026-01-15 13:00 | 9.98x | Full-bodied bullish | Flat / fading | -0.081% / -0.150% / -0.019% | Weak move without breakout | 97.1% | 2.9% | 0.0% | 2.49x | 0.019% / 0.249% |
| 2026-01-15 19:30 | 3.06x | Bearish pin-bar / upper rejection | Flat / fading | -0.012% / 0.087% / 0.100% | Position building in range | 34.5% | 44.8% | 20.7% | 2.56x | 0.162% / 0.044% |
| 2026-01-16 09:30 | 2.78x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.025% / -0.037% / 0.255% | True breakout | 47.2% | 47.2% | 5.6% | 2.42x | 0.304% / 0.099% |
| 2026-01-16 10:30 | 6.63x | Full-bodied bullish | Impulse / continuation | 0.124% / 0.551% / 0.545% | True breakout | 77.3% | 18.2% | 4.5% | 2.39x | 0.693% / 0.050% |
| 2026-01-16 10:45 | 3.26x | Full-bodied bullish | Impulse / continuation | 0.427% / 0.433% / 0.501% | True breakout | 62.5% | 12.5% | 25.0% | 1.61x | 0.569% / 0.000% |
| 2026-01-16 11:00 | 10.52x | Full-bodied bullish | Flat / fading | 0.006% / -0.006% / 0.043% | Weak move without breakout | 80.2% | 19.8% | 0.0% | 4.04x | 0.142% / 0.074% |
| 2026-01-16 16:30 | 5.57x | Full-bodied bullish | Impulse / continuation | 0.116% / 0.172% / -0.074% | True breakout | 66.0% | 34.0% | 0.0% | 5.93x | 0.380% / 0.129% |
| 2026-01-16 16:45 | 6.33x | Bearish pin-bar / upper rejection | Reversal | 0.055% / -0.024% / -0.196% | Liquidity sweep / reversal | 29.0% | 62.3% | 8.7% | 3.10x | 0.141% / 0.245% |
| 2026-01-16 23:15 | 2.51x | Full-bodied bullish | Reversal | -0.080% / -0.141% / 0.000% | Liquidity sweep / reversal | 61.3% | 6.5% | 32.3% | 2.08x | 0.037% / 0.165% |
| 2026-01-17 18:15 | 3.92x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.000% / 0.025% / 0.012% | True breakout | 44.4% | 55.6% | 0.0% | 1.48x | 0.086% / 0.025% |
| 2026-01-17 18:30 | 2.61x | Bearish pin-bar / upper rejection | Reversal | 0.025% / 0.012% / -0.043% | Liquidity sweep / reversal | 12.5% | 50.0% | 37.5% | 1.26x | 0.061% / 0.086% |
| 2026-01-18 10:00 | 3.52x | Doji / upper rejection | Impulse / continuation | -0.055% / -0.061% / -0.043% | True breakout | 0.0% | 66.7% | 33.3% | 2.60x | 0.086% / 0.086% |
| 2026-01-18 10:15 | 4.18x | Small-body bearish | Flat / fading | -0.006% / 0.000% / 0.025% | Weak move without breakout | 58.3% | 16.7% | 25.0% | 1.57x | 0.031% / 0.025% |
| 2026-01-18 17:15 | 4.51x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / 0.006% / 0.006% | Weak move without breakout | 16.7% | 0.0% | 83.3% | 1.68x | 0.006% / 0.031% |
| 2026-01-18 17:45 | 3.81x | Full-bodied bullish | Impulse / continuation | -0.006% / 0.000% / 0.012% | True breakout | 66.7% | 0.0% | 33.3% | 1.56x | 0.031% / 0.012% |
| 2026-01-18 18:30 | 3.18x | Doji | Impulse / continuation | 0.012% / 0.080% / 0.129% | True breakout | 0.0% | 60.0% | 40.0% | 1.32x | 0.257% / 0.257% |
| 2026-01-19 07:00 | 20.32x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.018% / 0.043% / 0.067% | True breakout | 40.7% | 48.1% | 11.1% | 6.00x | 0.141% / 0.061% |
| 2026-01-19 07:15 | 6.19x | Bearish pin-bar / upper rejection | Reversal | 0.061% / 0.080% / 0.012% | Liquidity sweep / reversal | 10.7% | 64.3% | 25.0% | 4.51x | 0.012% / 0.159% |
| 2026-01-19 08:00 | 3.02x | Bearish pin-bar / upper rejection | Reversal | -0.073% / -0.067% / -0.110% | Liquidity sweep / reversal | 6.7% | 80.0% | 13.3% | 1.58x | 0.012% / 0.153% |
| 2026-01-19 09:00 | 5.80x | Bullish pin-bar / lower rejection | Reversal | -0.055% / 0.080% / -0.031% | Liquidity sweep / reversal | 25.0% | 31.2% | 43.7% | 1.30x | 0.171% / 0.098% |
| 2026-01-19 09:15 | 2.68x | Bearish pin-bar / upper rejection | Reversal | 0.135% / 0.012% / 0.092% | Liquidity sweep / reversal | 33.3% | 59.3% | 7.4% | 2.08x | 0.116% / 0.141% |
| 2026-01-19 09:30 | 3.02x | Small-body bullish | Reversal | -0.122% / -0.110% / 0.000% | Liquidity sweep / reversal | 59.4% | 3.1% | 37.5% | 2.16x | 0.000% / 0.251% |
| 2026-01-19 09:45 | 2.97x | Full-bodied bearish | Impulse -> reversal | 0.012% / 0.080% / 0.153% | False breakout | 70.8% | 12.5% | 16.7% | 1.41x | 0.129% / 0.184% |
| 2026-01-19 10:00 | 4.12x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.067% / 0.110% / 0.196% | True breakout | 9.1% | 30.3% | 60.6% | 1.80x | 0.269% / 0.024% |
| 2026-01-19 10:45 | 2.23x | Small-body bullish | Impulse / continuation | 0.055% / 0.116% / 0.373% | True breakout | 35.7% | 35.7% | 28.6% | 0.70x | 0.544% / 0.006% |
| 2026-01-19 11:00 | 2.75x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.061% / 0.361% / 0.232% | True breakout | 45.5% | 54.5% | 0.0% | 1.15x | 0.489% / 0.000% |
| 2026-01-19 11:15 | 4.77x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.299% / 0.257% / 0.165% | True breakout | 18.2% | 81.8% | 0.0% | 2.84x | 0.428% / 0.000% |
| 2026-01-19 11:30 | 4.89x | Full-bodied bullish | Flat / fading | -0.043% / -0.128% / -0.091% | Position building in range | 70.0% | 30.0% | 0.0% | 3.10x | 0.073% / 0.158% |
| 2026-01-19 15:15 | 3.27x | Full-bodied bullish | Flat / fading | -0.036% / -0.024% / 0.055% | Weak move without breakout | 70.7% | 24.1% | 5.2% | 2.31x | 0.103% / 0.067% |
| 2026-01-20 07:00 | 4.23x | Small-body bullish | Flat / fading | 0.030% / 0.103% / 0.085% | Weak move without breakout | 30.6% | 38.9% | 30.6% | 2.70x | 0.121% / 0.006% |
| 2026-01-20 10:00 | 6.48x | Full-bodied bearish | Impulse / continuation | -0.067% / -0.170% / -0.170% | True breakout | 73.3% | 4.4% | 22.2% | 2.30x | 0.310% / 0.000% |
| 2026-01-20 10:15 | 3.03x | Small-body bearish | Impulse / continuation | -0.103% / -0.122% / -0.170% | True breakout | 58.8% | 5.9% | 35.3% | 0.78x | 0.249% / 0.049% |
| 2026-01-20 11:30 | 2.79x | Bearish pin-bar / upper rejection | Reversal | 0.219% / 0.262% / 0.134% | Liquidity sweep / reversal | 18.0% | 42.0% | 40.0% | 2.10x | 0.018% / 0.298% |
| 2026-01-20 17:15 | 5.62x | Full-bodied bullish | Flat / fading | 0.012% / -0.073% / -0.073% | Weak move without breakout | 89.8% | 5.7% | 4.5% | 3.77x | 0.121% / 0.158% |
| 2026-01-21 07:00 | 4.01x | Bearish pin-bar / upper rejection | Reversal | 0.067% / 0.140% / 0.006% | Liquidity sweep / reversal | 36.4% | 45.5% | 18.2% | 2.84x | 0.109% / 0.140% |
| 2026-01-21 09:00 | 2.67x | Bullish pin-bar / lower rejection | Reversal | 0.012% / -0.109% / 0.006% | Liquidity sweep / reversal | 27.3% | 18.2% | 54.5% | 1.16x | 0.067% / 0.109% |
| 2026-01-21 12:15 | 7.11x | Full-bodied bullish | Impulse / continuation | 0.079% / 0.073% / 0.735% | True breakout | 63.3% | 35.0% | 1.7% | 3.07x | 0.948% / 0.018% |
| 2026-01-21 12:30 | 6.35x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.006% / 0.067% / 0.765% | True breakout | 28.9% | 71.1% | 0.0% | 2.00x | 0.868% / 0.097% |
| 2026-01-21 13:15 | 8.09x | Full-bodied bullish | Impulse / continuation | 0.109% / 0.139% / 0.253% | True breakout | 71.9% | 25.2% | 2.9% | 5.72x | 0.392% / 0.036% |
| 2026-01-21 13:30 | 2.71x | Bearish pin-bar / upper rejection | Flat / fading | 0.030% / 0.151% / 0.139% | Weak move without breakout | 48.8% | 41.5% | 9.8% | 1.28x | 0.283% / 0.120% |
| 2026-01-22 07:00 | 5.28x | Bearish pin-bar / upper rejection | Reversal | -0.006% / -0.012% / -0.090% | Liquidity sweep / reversal | 29.3% | 68.3% | 2.4% | 2.13x | 0.018% / 0.155% |
| 2026-01-22 10:00 | 4.67x | Full-bodied bullish | Impulse / continuation | 0.060% / 0.132% / 0.030% | True breakout | 63.8% | 13.0% | 23.2% | 3.93x | 0.329% / 0.054% |
| 2026-01-22 10:30 | 4.90x | Bearish pin-bar / upper rejection | Reversal | -0.090% / -0.102% / -0.149% | Liquidity sweep / reversal | 22.4% | 67.3% | 10.2% | 2.22x | 0.006% / 0.221% |
| 2026-01-22 16:15 | 10.39x | Full-bodied bearish | Impulse / continuation | 0.048% / 0.024% / -0.372% | True breakout | 63.6% | 3.0% | 33.3% | 6.06x | 0.595% / 0.108% |
| 2026-01-22 17:00 | 2.99x | Bullish pin-bar / lower rejection | Reversal | -0.078% / 0.163% / 0.319% | Liquidity sweep / reversal | 54.5% | 0.0% | 45.5% | 3.28x | 0.301% / 0.482% |
| 2026-01-22 17:15 | 4.08x | Bullish pin-bar / lower rejection | Reversal | 0.241% / 0.458% / 0.440% | Liquidity sweep / reversal | 24.5% | 0.0% | 75.5% | 1.36x | 0.096% / 0.561% |
| 2026-01-22 17:30 | 2.97x | Bearish pin-bar / upper rejection | Flat / fading | 0.217% / 0.156% / 0.144% | Weak move without breakout | 40.2% | 45.1% | 14.7% | 2.64x | 0.319% / 0.054% |
| 2026-01-23 07:00 | 8.21x | Bullish pin-bar / lower rejection | Flat / fading | 0.102% / 0.042% / 0.102% | Weak move without breakout | 31.1% | 8.2% | 60.7% | 6.04x | 0.150% / 0.066% |
| 2026-01-23 10:15 | 2.69x | Bearish pin-bar / upper rejection | Reversal | 0.060% / 0.006% / 0.205% | Liquidity sweep / reversal | 44.1% | 44.1% | 11.8% | 1.20x | 0.078% / 0.289% |
| 2026-01-23 11:15 | 3.05x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.144% / 0.126% / 0.072% | True breakout | 42.3% | 53.8% | 3.8% | 1.22x | 0.258% / 0.006% |
| 2026-01-23 16:45 | 3.26x | Full-bodied bearish | Flat / fading | 0.066% / 0.066% / 0.042% | Position building in range | 81.8% | 18.2% | 0.0% | 2.00x | 0.000% / 0.108% |
| 2026-01-23 20:30 | 6.81x | Full-bodied bullish | Impulse / continuation | 0.006% / 0.156% / 0.120% | True breakout | 76.5% | 20.6% | 2.9% | 3.75x | 0.390% / 0.042% |
| 2026-01-23 20:45 | 5.38x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.150% / 0.258% / 0.066% | True breakout | 2.7% | 78.4% | 18.9% | 3.52x | 0.384% / -0.012% |
| 2026-01-23 21:00 | 2.71x | Full-bodied bullish | Impulse / continuation | 0.108% / -0.036% / -0.030% | True breakout | 65.7% | 34.3% | 0.0% | 2.83x | 0.234% / 0.120% |
| 2026-01-23 21:15 | 4.02x | Bearish pin-bar / upper rejection | Reversal | -0.144% / -0.192% / -0.150% | Liquidity sweep / reversal | 37.5% | 52.5% | 10.0% | 2.76x | 0.024% / 0.227% |
| 2026-01-24 13:15 | 3.40x | Full-bodied bearish | Flat / fading | 0.199% / 0.193% / 0.217% | Position building in range | 87.8% | 8.2% | 4.1% | 4.13x | 0.012% / 0.283% |
| 2026-01-24 15:30 | 2.97x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.283% / 0.187% / 0.193% | True breakout | 29.6% | 14.8% | 55.6% | 1.34x | 0.403% / 0.030% |
| 2026-01-24 15:45 | 5.14x | Full-bodied bullish | Flat / fading | -0.096% / -0.102% / -0.132% | Position building in range | 69.4% | 27.8% | 2.8% | 3.38x | 0.066% / 0.162% |
| 2026-01-25 12:30 | 5.93x | Full-bodied bullish | Flat / fading | -0.096% / -0.048% / -0.114% | Weak move without breakout | 91.7% | 8.3% | 0.0% | 4.17x | 0.060% / 0.120% |
| 2026-01-25 18:45 | 4.16x | Full-bodied bearish | Impulse / continuation | -0.054% / 0.000% / -0.036% | True breakout | 90.9% | 9.1% | 0.0% | 1.56x | 0.108% / 0.144% |
| 2026-01-26 07:00 | 11.94x | Bearish pin-bar / upper rejection | Reversal | -0.048% / -0.036% / -0.066% | Liquidity sweep / reversal | 26.3% | 63.2% | 10.5% | 4.93x | 0.024% / 0.108% |
| 2026-01-26 09:00 | 11.66x | Bullish pin-bar / lower rejection | Flat / fading | -0.030% / 0.000% / -0.096% | Position building in range | 41.1% | 0.0% | 58.9% | 4.06x | 0.198% / 0.042% |
| 2026-01-26 10:00 | 3.06x | Bullish pin-bar / lower rejection | Reversal | 0.072% / 0.024% / -0.054% | Liquidity sweep / reversal | 3.6% | 39.3% | 57.1% | 1.42x | 0.181% / 0.162% |
| 2026-01-26 14:30 | 2.52x | Bullish pin-bar / lower rejection | Flat / fading | -0.066% / -0.060% / -0.066% | Weak move without breakout | 44.1% | 8.8% | 47.1% | 1.79x | 0.163% / 0.000% |
| 2026-01-26 16:15 | 4.62x | Full-bodied bullish | Reversal | -0.078% / -0.187% / -0.235% | Liquidity sweep / reversal | 63.3% | 26.7% | 10.0% | 3.64x | 0.012% / 0.295% |
| 2026-01-27 07:00 | 4.33x | Bearish pin-bar / upper rejection | Flat / fading | 0.054% / -0.030% / 0.018% | Position building in range | 44.0% | 56.0% | 0.0% | 2.43x | 0.066% / 0.060% |
| 2026-01-27 10:30 | 3.99x | Bullish pin-bar / lower rejection | Flat / fading | 0.006% / -0.109% / -0.006% | Weak move without breakout | 32.0% | 0.0% | 68.0% | 1.66x | 0.157% / 0.036% |
| 2026-01-27 11:00 | 3.23x | Full-bodied bearish | Reversal | 0.060% / 0.103% / 0.139% | Liquidity sweep / reversal | 66.7% | 3.7% | 29.6% | 1.77x | 0.024% / 0.199% |
| 2026-01-27 13:45 | 3.02x | Full-bodied bullish | Impulse / continuation | 0.108% / 0.132% / 0.138% | True breakout | 90.6% | 9.4% | 0.0% | 1.76x | 0.235% / 0.054% |
| 2026-01-27 14:00 | 2.50x | Full-bodied bullish | Impulse / continuation | 0.024% / 0.024% / -0.084% | True breakout | 64.3% | 3.6% | 32.1% | 1.47x | 0.126% / 0.096% |
| 2026-01-27 14:15 | 2.80x | Bearish pin-bar / upper rejection | Reversal | 0.000% / 0.006% / -0.078% | Liquidity sweep / reversal | 33.3% | 53.3% | 13.3% | 0.78x | 0.102% / 0.138% |
| 2026-01-28 07:15 | 2.69x | Full-bodied bearish | Flat / fading | 0.096% / 0.090% / 0.090% | Position building in range | 71.4% | 10.7% | 17.9% | 1.93x | -0.006% / 0.138% |
| 2026-01-28 09:45 | 4.18x | Full-bodied bullish | Reversal | -0.257% / -0.143% / -0.269% | Liquidity sweep / reversal | 78.3% | 13.0% | 8.7% | 2.95x | 0.042% / 0.430% |
| 2026-01-28 10:00 | 5.35x | Full-bodied bearish | Impulse / continuation | 0.114% / -0.084% / -0.054% | True breakout | 74.5% | 16.4% | 9.1% | 3.14x | 0.174% / 0.132% |
| 2026-01-28 10:15 | 2.81x | Small-body bullish | Reversal | -0.197% / -0.126% / -0.203% | Liquidity sweep / reversal | 58.1% | 6.5% | 35.5% | 1.50x | 0.018% / 0.287% |
| 2026-01-28 10:30 | 2.64x | Full-bodied bearish | Flat / fading | 0.072% / 0.030% / 0.000% | Weak move without breakout | 91.7% | 8.3% | 0.0% | 1.64x | 0.090% / 0.150% |
| 2026-01-28 16:30 | 4.50x | Small-body bullish | Flat / fading | 0.012% / 0.054% / 0.036% | Weak move without breakout | 50.0% | 10.0% | 40.0% | 3.26x | 0.084% / 0.048% |
| 2026-01-28 17:15 | 2.78x | Bullish pin-bar / lower rejection | Reversal | -0.036% / -0.054% / -0.138% | Liquidity sweep / reversal | 15.0% | 0.0% | 85.0% | 1.37x | 0.012% / 0.168% |
| 2026-01-28 23:30 | 2.71x | Small-body bullish | Impulse / continuation | 0.000% / 0.096% / 0.168% | True breakout | 54.5% | 9.1% | 36.4% | 1.33x | 0.186% / 0.030% |
| 2026-01-29 07:00 | 3.54x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.024% / 0.060% | True breakout | 80.0% | 13.3% | 6.7% | 1.69x | 0.102% / 0.042% |
| 2026-01-29 09:15 | 2.75x | Small-body bullish | Impulse / continuation | 0.054% / 0.018% / 0.569% | True breakout | 38.5% | 38.5% | 23.1% | 1.21x | 0.623% / 0.048% |
| 2026-01-29 09:30 | 6.69x | Small-body bullish | Impulse / continuation | -0.036% / 0.299% / 0.449% | True breakout | 43.5% | 26.1% | 30.4% | 2.06x | 0.569% / 0.054% |
| 2026-01-29 09:45 | 3.43x | Bearish pin-bar / upper rejection | Reversal | 0.335% / 0.551% / 0.515% | Liquidity sweep / reversal | 16.7% | 66.7% | 16.7% | 1.45x | 0.000% / 0.605% |
| 2026-01-29 10:00 | 17.05x | Full-bodied bullish | Impulse / continuation | 0.215% / 0.149% / 0.621% | True breakout | 64.0% | 34.9% | 1.2% | 6.65x | 0.633% / 0.072% |
| 2026-01-29 10:15 | 5.37x | Full-bodied bullish | Impulse / continuation | -0.066% / -0.036% / 0.274% | True breakout | 63.2% | 15.8% | 21.1% | 3.05x | 0.423% / 0.161% |
| 2026-01-29 10:30 | 2.76x | Bullish pin-bar / lower rejection | Reversal | 0.030% / 0.471% / 0.274% | Liquidity sweep / reversal | 55.0% | 0.0% | 45.0% | 0.92x | 0.095% / 0.489% |
| 2026-01-29 11:00 | 4.75x | Full-bodied bullish | Flat / fading | -0.131% / -0.196% / -0.095% | Weak move without breakout | 88.0% | 2.4% | 9.6% | 3.56x | 0.018% / 0.267% |
| 2026-01-29 17:00 | 2.52x | Full-bodied bullish | Reversal | 0.041% / -0.112% / -0.660% | Liquidity sweep / reversal | 91.1% | 2.2% | 6.7% | 1.85x | 0.094% / 0.737% |
| 2026-01-29 18:00 | 3.69x | Full-bodied bearish | Impulse / continuation | -0.273% / -0.303% / -0.285% | True breakout | 77.0% | 8.0% | 14.9% | 3.05x | 0.552% / 0.018% |
| 2026-01-29 18:15 | 4.49x | Full-bodied bearish | Flat / fading | -0.030% / -0.143% / -0.161% | Weak move without breakout | 64.8% | 4.2% | 31.0% | 2.12x | 0.286% / 0.173% |
| 2026-01-30 07:00 | 2.63x | Small-body bullish | Reversal | -0.385% / -0.367% / -0.337% | Liquidity sweep / reversal | 32.1% | 30.4% | 37.5% | 2.17x | 0.012% / 0.491% |
| 2026-01-30 09:15 | 2.51x | Bullish pin-bar / lower rejection | Flat / fading | 0.095% / 0.065% / 0.160% | Weak move without breakout | 40.5% | 4.8% | 54.8% | 1.35x | 0.178% / 0.083% |
| 2026-01-30 11:15 | 5.74x | Full-bodied bearish | Impulse / continuation | -0.185% / -0.466% / -0.430% | True breakout | 67.8% | 10.2% | 22.0% | 3.78x | 0.520% / -0.018% |
| 2026-01-30 11:30 | 4.61x | Full-bodied bearish | Impulse / continuation | -0.281% / -0.221% / -0.251% | True breakout | 65.1% | 0.0% | 34.9% | 1.14x | 0.335% / 0.060% |
| 2026-01-30 11:45 | 3.09x | Full-bodied bearish | Flat / fading | 0.060% / 0.036% / 0.204% | Weak move without breakout | 74.2% | 17.7% | 8.1% | 1.58x | 0.054% / 0.276% |
| 2026-01-30 20:30 | 3.24x | Full-bodied bearish | Impulse / continuation | -0.240% / -0.120% / -0.072% | True breakout | 97.2% | 2.8% | 0.0% | 1.79x | 0.342% / 0.132% |
| 2026-01-30 20:45 | 5.27x | Full-bodied bearish | Flat / fading | 0.120% / 0.102% / 0.181% | Weak move without breakout | 76.9% | 1.9% | 21.2% | 2.68x | 0.102% / 0.373% |
| 2026-01-30 21:00 | 2.77x | Bearish pin-bar / upper rejection | Flat / fading | -0.018% / 0.048% / 0.018% | Weak move without breakout | 29.0% | 60.9% | 10.1% | 3.39x | 0.114% / 0.222% |
| 2026-01-31 13:15 | 3.26x | Small-body bullish | Flat / fading | -0.012% / -0.030% / -0.036% | Position building in range | 55.0% | 30.0% | 15.0% | 2.15x | 0.012% / 0.066% |
| 2026-01-31 18:30 | 10.07x | Bearish pin-bar / upper rejection | Reversal | -0.030% / -0.030% / -0.012% | Liquidity sweep / reversal | 11.1% | 77.8% | 11.1% | 6.00x | 0.018% / 0.084% |
| 2026-02-01 13:00 | 3.63x | Bullish pin-bar / lower rejection | Reversal | 0.024% / 0.132% / 0.120% | Liquidity sweep / reversal | 37.5% | 12.5% | 50.0% | 1.23x | 0.036% / 0.222% |
| 2026-02-01 13:15 | 2.87x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.108% / 0.192% / 0.150% | True breakout | 40.0% | 0.0% | 60.0% | 1.65x | 0.198% / 0.018% |
| 2026-02-01 13:30 | 5.72x | Full-bodied bullish | Flat / fading | 0.084% / -0.012% / 0.024% | Weak move without breakout | 63.3% | 30.0% | 6.7% | 4.42x | 0.090% / 0.078% |
| 2026-02-01 14:00 | 5.08x | Bullish pin-bar / lower rejection | Flat / fading | 0.054% / 0.036% / 0.012% | Position building in range | 59.3% | 0.0% | 40.7% | 3.07x | 0.024% / 0.060% |
| 2026-02-01 14:45 | 2.77x | Bearish pin-bar / upper rejection | Flat / fading | -0.024% / -0.006% / -0.024% | Weak move without breakout | 50.0% | 50.0% | 0.0% | 0.20x | 0.042% / 0.012% |
| 2026-02-02 07:00 | 8.51x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.036% / 0.030% / -0.072% | True breakout | 54.1% | 40.5% | 5.4% | 4.71x | 0.078% / 0.048% |
| 2026-02-02 07:45 | 2.88x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.048% / -0.054% / -0.174% | True breakout | 47.4% | 10.5% | 42.1% | 1.80x | 0.192% / 0.066% |
| 2026-02-02 08:30 | 2.98x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.066% / -0.228% / -0.132% | True breakout | 40.9% | 45.5% | 13.6% | 1.86x | 0.276% / 0.018% |
| 2026-02-02 08:45 | 2.52x | Full-bodied bearish | Impulse / continuation | -0.162% / -0.090% / -0.108% | True breakout | 64.7% | 17.6% | 17.6% | 1.30x | 0.210% / 0.084% |
| 2026-02-02 09:00 | 6.37x | Small-body bearish | Flat / fading | 0.072% / 0.096% / -0.060% | Weak move without breakout | 55.1% | 28.6% | 16.3% | 3.67x | 0.108% / 0.162% |
| 2026-02-02 09:45 | 3.32x | Bullish pin-bar / lower rejection | Reversal | -0.114% / 0.096% / 0.090% | Liquidity sweep / reversal | 28.0% | 12.0% | 60.0% | 1.46x | 0.198% / 0.132% |
| 2026-02-02 10:00 | 3.03x | Full-bodied bearish | Reversal | 0.211% / 0.120% / -0.024% | Liquidity sweep / reversal | 60.6% | 15.2% | 24.2% | 1.80x | 0.084% / 0.247% |
| 2026-02-02 10:15 | 2.68x | Full-bodied bullish | Reversal | -0.090% / -0.006% / -0.252% | Liquidity sweep / reversal | 69.1% | 10.9% | 20.0% | 2.70x | 0.024% / 0.385% |
| 2026-02-02 12:45 | 2.52x | Full-bodied bullish | Reversal | -0.066% / -0.078% / -0.210% | Liquidity sweep / reversal | 94.1% | 2.9% | 2.9% | 1.21x | 0.066% / 0.228% |
| 2026-02-03 07:00 | 3.22x | Small-body bullish | Impulse / continuation | -0.012% / 0.198% / 0.276% | True breakout | 51.7% | 13.8% | 34.5% | 2.37x | 0.396% / 0.060% |
| 2026-02-03 07:30 | 3.96x | Full-bodied bullish | Impulse / continuation | -0.090% / 0.078% / 0.054% | True breakout | 67.3% | 32.7% | 0.0% | 3.94x | 0.198% / 0.174% |
| 2026-02-03 07:45 | 4.38x | Bearish pin-bar / upper rejection | Reversal | 0.168% / 0.180% / 0.078% | Liquidity sweep / reversal | 24.2% | 53.2% | 22.6% | 3.82x | 0.066% / 0.228% |
| 2026-02-03 08:45 | 2.68x | Bullish pin-bar / lower rejection | Flat / fading | -0.102% / -0.012% / -0.084% | Position building in range | 28.6% | 2.9% | 68.6% | 1.58x | 0.120% / 0.000% |
| 2026-02-03 10:00 | 31.41x | Small-body bullish | Impulse / continuation | 0.214% / 0.529% / 0.405% | True breakout | 56.1% | 32.2% | 11.7% | 9.00x | 0.684% / 0.024% |
| 2026-02-03 10:15 | 3.02x | Full-bodied bullish | Impulse / continuation | 0.315% / 0.208% / 0.237% | True breakout | 64.3% | 28.6% | 7.1% | 1.47x | 0.469% / -0.006% |
| 2026-02-03 10:30 | 4.34x | Full-bodied bullish | Flat / fading | -0.107% / -0.124% / -0.266% | Weak move without breakout | 66.7% | 33.3% | 0.0% | 1.89x | 0.000% / 0.379% |
| 2026-02-04 07:00 | 4.05x | Bearish pin-bar / upper rejection | Reversal | 0.036% / 0.042% / 0.125% | Liquidity sweep / reversal | 2.1% | 62.5% | 35.4% | 2.90x | 0.054% / 0.149% |
| 2026-02-04 09:45 | 3.59x | Full-bodied bullish | Impulse / continuation | -0.018% / -0.018% / 0.018% | True breakout | 87.8% | 4.1% | 8.2% | 2.85x | 0.172% / 0.101% |
| 2026-02-04 10:00 | 5.39x | Bearish pin-bar / upper rejection | Reversal | 0.000% / 0.018% / 0.000% | Liquidity sweep / reversal | 7.1% | 69.0% | 23.8% | 2.13x | 0.083% / 0.077% |
| 2026-02-04 12:30 | 3.16x | Small-body bearish | Flat / fading | -0.012% / -0.053% / 0.000% | Weak move without breakout | 53.6% | 14.3% | 32.1% | 1.39x | 0.071% / 0.059% |
| 2026-02-04 16:15 | 3.02x | Small-body bearish | Reversal | 0.048% / 0.089% / 0.065% | Liquidity sweep / reversal | 46.2% | 15.4% | 38.5% | 1.81x | 0.065% / 0.107% |
| 2026-02-04 18:15 | 2.67x | Full-bodied bearish | Impulse / continuation | 0.066% / 0.113% / -0.334% | True breakout | 95.7% | 2.1% | 2.1% | 2.74x | 0.358% / 0.137% |
| 2026-02-04 19:00 | 3.33x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.269% / -0.179% / -0.382% | True breakout | 41.0% | 14.8% | 44.3% | 3.42x | 0.412% / 0.012% |
| 2026-02-05 07:00 | 3.15x | Small-body bearish | Impulse / continuation | 0.048% / 0.084% / -0.120% | True breakout | 37.5% | 32.5% | 30.0% | 2.71x | 0.174% / 0.090% |
| 2026-02-05 09:15 | 2.67x | Bullish pin-bar / lower rejection | Reversal | 0.060% / -0.084% / 0.186% | Liquidity sweep / reversal | 56.2% | 0.0% | 43.8% | 1.00x | 0.210% / 0.144% |
| 2026-02-05 09:45 | 2.84x | Full-bodied bearish | Reversal | 0.090% / 0.270% / 0.510% | Liquidity sweep / reversal | 66.7% | 33.3% | 0.0% | 2.07x | 0.060% / 0.534% |
| 2026-02-05 10:00 | 6.29x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.180% / 0.336% / 0.360% | True breakout | 42.9% | 10.7% | 46.4% | 1.46x | 0.444% / 0.060% |
| 2026-02-05 10:15 | 3.27x | Full-bodied bullish | Impulse / continuation | 0.156% / 0.239% / 0.419% | True breakout | 68.2% | 9.1% | 22.7% | 2.15x | 0.479% / 0.012% |
| 2026-02-05 10:30 | 3.19x | Full-bodied bullish | Impulse / continuation | 0.084% / 0.024% / 0.347% | True breakout | 72.2% | 22.2% | 5.6% | 1.55x | 0.353% / 0.048% |
| 2026-02-05 11:00 | 3.07x | Bullish pin-bar / lower rejection | Reversal | 0.239% / 0.323% / 0.239% | Liquidity sweep / reversal | 50.0% | 5.0% | 45.0% | 0.83x | 0.018% / 0.329% |
| 2026-02-05 11:15 | 2.87x | Full-bodied bullish | Flat / fading | 0.083% / 0.030% / 0.095% | Weak move without breakout | 75.5% | 18.9% | 5.7% | 2.14x | 0.101% / 0.048% |
| 2026-02-05 13:15 | 2.85x | Full-bodied bearish | Flat / fading | 0.006% / 0.066% / -0.054% | Weak move without breakout | 83.5% | 1.3% | 15.2% | 2.58x | 0.096% / 0.275% |
| 2026-02-05 14:30 | 2.64x | Full-bodied bearish | Impulse / continuation | -0.012% / -0.205% / -0.048% | True breakout | 88.4% | 3.2% | 8.4% | 2.94x | 0.265% / 0.151% |
| 2026-02-06 07:00 | 4.64x | Full-bodied bullish | Flat / fading | 0.000% / 0.030% / -0.030% | Weak move without breakout | 62.7% | 15.3% | 22.0% | 3.70x | 0.060% / 0.090% |
| 2026-02-06 10:00 | 5.49x | Small-body bearish | Impulse / continuation | -0.133% / -0.121% / -0.181% | True breakout | 52.6% | 31.6% | 15.8% | 2.57x | 0.272% / 0.000% |
| 2026-02-06 10:30 | 2.83x | Bullish pin-bar / lower rejection | Reversal | -0.091% / -0.060% / -0.060% | Liquidity sweep / reversal | 9.5% | 28.6% | 61.9% | 1.19x | 0.000% / 0.151% |
| 2026-02-06 12:30 | 2.82x | Full-bodied bullish | Impulse / continuation | 0.048% / 0.103% / 0.224% | True breakout | 62.9% | 34.3% | 2.9% | 1.90x | 0.314% / 0.042% |
| 2026-02-06 13:15 | 3.44x | Full-bodied bullish | Reversal | -0.078% / -0.175% / -0.325% | Liquidity sweep / reversal | 94.3% | 5.7% | 0.0% | 1.60x | 0.012% / 0.349% |
| 2026-02-06 16:45 | 6.95x | Full-bodied bearish | Flat / fading | 0.091% / 0.134% / 0.006% | Weak move without breakout | 88.8% | 0.0% | 11.2% | 4.75x | 0.164% / 0.231% |
| 2026-02-06 17:00 | 2.68x | Bullish pin-bar / lower rejection | Reversal | 0.042% / 0.024% / -0.140% | Liquidity sweep / reversal | 33.3% | 6.7% | 60.0% | 1.79x | 0.140% / 0.164% |
| 2026-02-06 23:00 | 2.60x | Small-body bearish | Impulse / continuation | -0.073% / -0.219% / -0.055% | True breakout | 52.9% | 8.8% | 38.2% | 3.22x | 0.255% / 0.018% |
| 2026-02-06 23:30 | 5.28x | Full-bodied bearish | Reversal | 0.043% / 0.164% / 0.231% | Liquidity sweep / reversal | 70.6% | 11.8% | 17.6% | 2.62x | 0.024% / 0.414% |
| 2026-02-07 18:15 | 3.14x | Bullish pin-bar / lower rejection | Reversal | 0.006% / 0.012% / 0.225% | Liquidity sweep / reversal | 22.2% | 22.2% | 55.6% | 1.37x | 0.030% / 0.231% |
| 2026-02-08 10:00 | 4.17x | Bullish pin-bar / lower rejection | Flat / fading | -0.036% / -0.061% / -0.073% | Weak move without breakout | 51.7% | 3.4% | 44.8% | 3.36x | 0.012% / 0.109% |
| 2026-02-09 07:00 | 19.63x | Full-bodied bearish | Flat / fading | -0.024% / 0.049% / -0.006% | Position building in range | 75.0% | 1.7% | 23.3% | 10.63x | 0.055% / 0.085% |
| 2026-02-09 07:15 | 4.97x | Bearish pin-bar / upper rejection | Reversal | 0.073% / 0.000% / -0.018% | Liquidity sweep / reversal | 10.5% | 63.2% | 26.3% | 2.00x | 0.030% / 0.110% |
| 2026-02-09 09:00 | 9.10x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.049% / 0.085% / -0.122% | True breakout | 51.4% | 2.9% | 45.7% | 2.47x | 0.189% / 0.177% |
| 2026-02-09 09:45 | 2.87x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.201% / -0.164% / -0.213% | True breakout | 3.7% | 55.6% | 40.7% | 1.57x | 0.280% / 0.012% |
| 2026-02-09 10:00 | 7.83x | Full-bodied bearish | Flat / fading | 0.037% / -0.012% / -0.159% | Weak move without breakout | 63.0% | 13.0% | 23.9% | 2.44x | 0.159% / 0.092% |
| 2026-02-09 10:15 | 3.00x | Bullish pin-bar / lower rejection | Reversal | -0.049% / -0.049% / -0.171% | Liquidity sweep / reversal | 17.9% | 32.1% | 50.0% | 1.29x | 0.055% / 0.226% |
| 2026-02-09 10:45 | 3.38x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.146% / -0.122% / -0.110% | True breakout | 4.3% | 69.6% | 26.1% | 1.23x | 0.201% / 0.098% |
| 2026-02-09 11:00 | 5.08x | Full-bodied bearish | Reversal | 0.024% / 0.024% / 0.177% | Liquidity sweep / reversal | 60.0% | 40.0% | 0.0% | 2.11x | 0.055% / 0.196% |
| 2026-02-09 15:15 | 2.21x | Small-body bullish | Impulse / continuation | 0.206% / 0.170% / 0.140% | True breakout | 58.8% | 32.4% | 8.8% | 3.63x | 0.249% / 0.024% |
| 2026-02-09 18:00 | 2.57x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.091% / -0.200% / -0.091% | True breakout | 28.6% | 71.4% | 0.0% | 2.16x | 0.261% / 0.036% |
| 2026-02-10 07:00 | 7.90x | Bullish pin-bar / lower rejection | Flat / fading | 0.048% / 0.079% / 0.042% | Weak move without breakout | 20.0% | 38.0% | 42.0% | 4.37x | 0.164% / 0.000% |
| 2026-02-10 10:00 | 3.55x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.345% / 0.236% / 0.000% | True breakout | 16.0% | 36.0% | 48.0% | 1.50x | 0.412% / 0.036% |
| 2026-02-10 10:15 | 9.80x | Full-bodied bullish | Reversal | -0.109% / -0.254% / -0.380% | Liquidity sweep / reversal | 81.9% | 15.3% | 2.8% | 4.11x | 0.018% / 0.435% |
| 2026-02-10 10:45 | 3.04x | Full-bodied bearish | Impulse / continuation | -0.091% / -0.127% / -0.206% | True breakout | 83.9% | 6.5% | 9.7% | 1.49x | 0.236% / 0.012% |
| 2026-02-10 17:00 | 3.97x | Full-bodied bullish | Reversal | -0.018% / -0.048% / -0.266% | Liquidity sweep / reversal | 62.2% | 2.7% | 35.1% | 2.22x | 0.012% / 0.321% |
| 2026-02-11 07:00 | 2.59x | Small-body bullish | Flat / fading | -0.030% / -0.018% / 0.055% | Weak move without breakout | 37.5% | 33.3% | 29.2% | 2.65x | 0.091% / 0.061% |
| 2026-02-11 08:00 | 2.65x | Small-body bullish | Impulse / continuation | 0.036% / 0.158% / 0.085% | True breakout | 55.6% | 33.3% | 11.1% | 1.88x | 0.170% / 0.030% |
| 2026-02-11 08:30 | 3.78x | Full-bodied bullish | Reversal | -0.048% / -0.073% / -0.151% | Liquidity sweep / reversal | 100.0% | 0.0% | 0.0% | 1.89x | 0.012% / 0.200% |
| 2026-02-11 09:30 | 3.47x | Full-bodied bearish | Impulse / continuation | 0.036% / -0.212% / 0.030% | True breakout | 63.6% | 0.0% | 36.4% | 1.67x | 0.303% / 0.182% |
| 2026-02-11 10:00 | 9.42x | Full-bodied bearish | Flat / fading | 0.067% / 0.243% / 0.243% | Weak move without breakout | 73.2% | 0.0% | 26.8% | 3.58x | 0.055% / 0.395% |
| 2026-02-11 10:15 | 3.07x | Small-body bullish | Impulse / continuation | 0.176% / 0.182% / 0.164% | True breakout | 45.8% | 16.7% | 37.5% | 1.27x | 0.328% / 0.024% |
| 2026-02-11 10:30 | 5.94x | Bearish pin-bar / upper rejection | Flat / fading | 0.006% / 0.000% / 0.164% | Weak move without breakout | 48.3% | 43.1% | 8.6% | 2.93x | 0.206% / 0.061% |
| 2026-02-11 12:45 | 7.47x | Full-bodied bullish | Flat / fading | -0.133% / -0.102% / -0.169% | Position building in range | 74.4% | 23.3% | 2.2% | 3.28x | 0.048% / 0.193% |
| 2026-02-11 15:30 | 4.11x | Full-bodied bullish | Impulse / continuation | 0.012% / 0.048% / 0.048% | True breakout | 73.7% | 16.1% | 10.2% | 4.53x | 0.276% / 0.120% |
| 2026-02-12 07:00 | 3.01x | Bullish pin-bar / lower rejection | Flat / fading | 0.006% / -0.024% / 0.000% | Position building in range | 60.0% | 0.0% | 40.0% | 4.19x | 0.036% / 0.060% |
| 2026-02-12 10:00 | 5.94x | Full-bodied bearish | Impulse / continuation | 0.120% / 0.048% / -0.042% | True breakout | 67.5% | 5.0% | 27.5% | 3.39x | 0.162% / 0.156% |
| 2026-02-12 11:00 | 4.06x | Bullish pin-bar / lower rejection | Reversal | 0.054% / 0.174% / 0.168% | Liquidity sweep / reversal | 3.2% | 32.3% | 64.5% | 2.04x | 0.006% / 0.210% |
| 2026-02-12 11:30 | 2.95x | Full-bodied bullish | Impulse / continuation | -0.066% / -0.006% / 0.300% | True breakout | 77.8% | 22.2% | 0.0% | 1.57x | 0.300% / 0.132% |
| 2026-02-12 12:15 | 6.06x | Small-body bullish | Impulse / continuation | 0.156% / 0.252% / 0.312% | True breakout | 58.1% | 23.3% | 18.6% | 2.28x | 0.348% / 0.036% |
| 2026-02-12 12:30 | 4.26x | Full-bodied bullish | Impulse / continuation | 0.096% / 0.132% / 0.078% | True breakout | 81.3% | 0.0% | 18.7% | 1.51x | 0.191% / 0.102% |
| 2026-02-12 12:45 | 3.74x | Small-body bullish | Flat / fading | 0.036% / 0.060% / 0.060% | Weak move without breakout | 50.0% | 13.2% | 36.8% | 1.66x | 0.096% / 0.149% |
| 2026-02-12 22:15 | 3.32x | Bearish pin-bar / upper rejection | Flat / fading | -0.042% / -0.036% / -0.024% | Position building in range | 17.8% | 57.8% | 24.4% | 3.99x | 0.018% / 0.078% |
| 2026-02-13 07:00 | 2.93x | Bearish pin-bar / upper rejection | Reversal | -0.102% / -0.066% / -0.030% | Liquidity sweep / reversal | 13.6% | 54.5% | 31.8% | 2.04x | 0.006% / 0.120% |
| 2026-02-13 09:15 | 3.71x | Full-bodied bearish | Flat / fading | 0.036% / -0.066% / 0.036% | Weak move without breakout | 65.8% | 2.6% | 31.6% | 3.64x | 0.132% / 0.072% |
| 2026-02-13 10:45 | 4.07x | Bullish pin-bar / lower rejection | Flat / fading | 0.048% / 0.018% / 0.018% | Weak move without breakout | 41.3% | 17.4% | 41.3% | 2.97x | 0.126% / 0.012% |
| 2026-02-13 12:15 | 3.21x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.114% / 0.060% / -0.180% | False breakout | 53.3% | 6.7% | 40.0% | 0.71x | 0.186% / 0.180% |
| 2026-02-13 12:30 | 4.57x | Small-body bullish | Reversal | -0.054% / -0.084% / 0.646% | Liquidity sweep / reversal | 46.5% | 20.9% | 32.6% | 2.01x | 0.981% / 0.419% |
| 2026-02-13 13:15 | 2.90x | Bearish pin-bar / upper rejection | Reversal | 0.942% / 1.164% / 1.002% | Liquidity sweep / reversal | 57.4% | 42.6% | 0.0% | 2.75x | 0.126% / 1.278% |
| 2026-02-13 13:30 | 21.49x | Full-bodied bullish | Flat / fading | 0.220% / 0.178% / 0.077% | Position building in range | 67.1% | 23.9% | 9.0% | 9.61x | 0.315% / 0.048% |
| 2026-02-13 14:00 | 2.98x | Bullish pin-bar / lower rejection | Flat / fading | -0.119% / -0.101% / -0.047% | Position building in range | 11.5% | 26.2% | 62.3% | 1.45x | 0.148% / 0.036% |
| 2026-02-13 23:45 | 2.59x | Full-bodied bullish | Impulse / continuation | 0.148% / 0.361% / 0.438% | True breakout | 88.9% | 0.0% | 11.1% | 0.88x | 0.480% / -0.148% |
| 2026-02-16 07:00 | 6.68x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.077% / 0.165% | True breakout | 64.3% | 35.7% | 0.0% | 5.26x | 0.277% / 0.071% |
| 2026-02-16 07:45 | 3.33x | Full-bodied bullish | Impulse / continuation | -0.059% / 0.059% / 0.012% | True breakout | 65.8% | 23.7% | 10.5% | 2.39x | 0.147% / 0.071% |
| 2026-02-16 08:30 | 4.12x | Bearish pin-bar / upper rejection | Reversal | -0.053% / -0.035% / 0.018% | Liquidity sweep / reversal | 12.5% | 87.5% | 0.0% | 0.85x | 0.082% / 0.124% |
| 2026-02-16 09:45 | 3.95x | Full-bodied bullish | Impulse / continuation | -0.018% / 0.018% / 0.147% | True breakout | 89.1% | 7.3% | 3.6% | 2.66x | 0.317% / 0.141% |
| 2026-02-16 10:00 | 7.47x | Doji / upper rejection | Flat / fading | 0.035% / -0.006% / 0.176% | Weak move without breakout | 0.0% | 93.4% | 6.6% | 2.53x | 0.188% / 0.188% |
| 2026-02-16 12:15 | 2.50x | Small-body bullish | Impulse / continuation | 0.035% / 0.292% / 0.730% | True breakout | 50.9% | 32.1% | 17.0% | 1.83x | 0.783% / 0.023% |
| 2026-02-16 13:00 | 2.88x | Full-bodied bullish | Flat / fading | 0.116% / -0.058% / -0.221% | Weak move without breakout | 88.5% | 9.8% | 1.6% | 1.75x | 0.168% / 0.255% |
| 2026-02-16 13:15 | 3.04x | Full-bodied bullish | Reversal | -0.174% / -0.278% / -0.481% | Liquidity sweep / reversal | 61.8% | 26.5% | 11.8% | 0.88x | 0.023% / 0.568% |
| 2026-02-16 16:30 | 2.65x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.422% / 0.439% / 0.312% | True breakout | 44.8% | 50.0% | 5.2% | 1.65x | 0.798% / 0.006% |
| 2026-02-16 16:45 | 2.75x | Full-bodied bullish | Impulse / continuation | 0.017% / 0.155% / -0.081% | True breakout | 79.3% | 19.6% | 1.1% | 2.63x | 0.374% / 0.184% |
| 2026-02-16 17:00 | 2.23x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.138% / -0.127% / -0.115% | False breakout | 4.2% | 27.1% | 68.8% | 1.23x | 0.357% / 0.316% |
| 2026-02-16 17:15 | 2.25x | Bearish pin-bar / upper rejection | Reversal | -0.264% / -0.236% / -0.448% | Liquidity sweep / reversal | 41.5% | 58.5% | 0.0% | 1.65x | 0.006% / 0.454% |
| 2026-02-16 23:15 | 3.01x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.247% / 0.385% / 0.494% | True breakout | 35.3% | 58.8% | 5.9% | 1.78x | 0.673% / 0.011% |
| 2026-02-16 23:30 | 3.87x | Full-bodied bullish | Impulse / continuation | 0.138% / 0.086% / 0.229% | True breakout | 64.3% | 35.7% | 0.0% | 3.66x | 0.424% / 0.086% |
| 2026-02-17 07:00 | 4.13x | Small-body bullish | Reversal | -0.017% / -0.503% / -0.441% | Liquidity sweep / reversal | 28.1% | 34.8% | 37.1% | 3.80x | 0.034% / 0.503% |
| 2026-02-17 07:30 | 2.72x | Full-bodied bearish | Flat / fading | 0.115% / 0.063% / 0.058% | Weak move without breakout | 98.8% | 1.2% | 0.0% | 3.11x | 0.075% / 0.236% |
| 2026-02-17 11:00 | 4.28x | Full-bodied bearish | Reversal | 0.098% / 0.242% / 0.628% | Liquidity sweep / reversal | 71.4% | 11.0% | 17.6% | 2.45x | 0.208% / 0.651% |
| 2026-02-17 11:15 | 3.71x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.144% / 0.121% / 0.518% | True breakout | 34.0% | 0.0% | 66.0% | 1.41x | 0.553% / 0.012% |
| 2026-02-18 07:00 | 2.76x | Full-bodied bearish | Impulse / continuation | -0.109% / -0.132% / -0.247% | True breakout | 64.3% | 2.4% | 33.3% | 3.02x | 0.270% / 0.000% |
| 2026-02-18 10:45 | 14.37x | Full-bodied bullish | Impulse / continuation | 0.217% / 0.091% / 0.006% | True breakout | 88.2% | 9.6% | 2.2% | 8.68x | 0.280% / 0.126% |
| 2026-02-18 11:00 | 8.29x | Full-bodied bullish | Flat / fading | -0.125% / -0.114% / -0.120% | Weak move without breakout | 62.3% | 18.0% | 19.7% | 1.91x | 0.028% / 0.342% |
| 2026-02-18 11:15 | 3.36x | Full-bodied bearish | Impulse / continuation | 0.011% / -0.086% / -0.200% | True breakout | 79.3% | 13.8% | 6.9% | 0.84x | 0.268% / 0.074% |
| 2026-02-18 18:00 | 3.97x | Full-bodied bullish | Impulse / continuation | 0.392% / 0.427% / 0.199% | True breakout | 100.0% | 0.0% | 0.0% | 2.77x | 0.518% / 0.011% |
| 2026-02-18 18:15 | 6.92x | Full-bodied bullish | Flat / fading | 0.034% / -0.040% / -0.164% | Position building in range | 74.2% | 23.7% | 2.2% | 2.57x | 0.074% / 0.255% |
| 2026-02-19 10:30 | 5.35x | Full-bodied bearish | Flat / fading | 0.102% / 0.085% / 0.216% | Position building in range | 95.8% | 3.2% | 1.1% | 4.28x | 0.000% / 0.416% |
| 2026-02-19 15:00 | 2.36x | Bullish pin-bar / lower rejection | Flat / fading | 0.011% / -0.011% / -0.091% | Weak move without breakout | 48.7% | 2.6% | 48.7% | 1.44x | 0.103% / 0.142% |
| 2026-02-20 07:00 | 4.11x | Small-body bearish | Flat / fading | 0.103% / 0.040% / 0.091% | Position building in range | 52.3% | 18.2% | 29.5% | 8.56x | 0.046% / 0.108% |
| 2026-02-20 09:15 | 3.85x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.023% / 0.068% / 0.324% | True breakout | 52.2% | 43.5% | 4.3% | 1.81x | 0.324% / 0.011% |
| 2026-02-20 09:45 | 3.37x | Bearish pin-bar / upper rejection | Reversal | -0.074% / 0.256% / 0.199% | Liquidity sweep / reversal | 41.7% | 58.3% | 0.0% | 1.67x | 0.387% / 0.080% |
| 2026-02-20 10:15 | 5.49x | Full-bodied bullish | Impulse / continuation | -0.085% / -0.057% / -0.096% | True breakout | 98.3% | 0.0% | 1.7% | 3.58x | 0.130% / 0.199% |
| 2026-02-20 10:30 | 4.08x | Bearish pin-bar / upper rejection | Flat / fading | 0.028% / 0.045% / -0.085% | Weak move without breakout | 36.8% | 63.2% | 0.0% | 1.84x | 0.114% / 0.131% |
| 2026-02-20 11:15 | 3.28x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.074% / -0.114% / -0.227% | True breakout | 37.9% | 0.0% | 62.1% | 1.52x | 0.346% / 0.023% |
| 2026-02-20 12:45 | 7.86x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.257% / -0.251% / -0.086% | True breakout | 42.0% | 5.1% | 52.9% | 5.32x | 0.628% / -0.006% |
| 2026-02-20 13:00 | 6.79x | Bullish pin-bar / lower rejection | Flat / fading | 0.006% / 0.195% / 0.218% | Position building in range | 40.4% | 0.0% | 59.6% | 3.19x | 0.258% / 0.229% |
| 2026-02-21 17:45 | 6.97x | Full-bodied bearish | Flat / fading | 0.023% / 0.023% / 0.029% | Position building in range | 85.7% | 14.3% | 0.0% | 2.04x | 0.000% / 0.029% |
| 2026-02-22 10:00 | 9.50x | Full-bodied bullish | Impulse / continuation | 0.085% / 0.085% / 0.165% | True breakout | 74.1% | 14.8% | 11.1% | 6.00x | 0.211% / 0.017% |
| 2026-02-22 10:15 | 14.97x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / 0.074% / 0.063% | Weak move without breakout | 44.1% | 47.1% | 8.8% | 5.53x | 0.125% / 0.045% |
| 2026-02-22 13:00 | 3.26x | Bullish pin-bar / lower rejection | Flat / fading | -0.011% / -0.028% / -0.051% | Weak move without breakout | 28.6% | 21.4% | 50.0% | 1.02x | 0.091% / 0.011% |
| 2026-02-22 18:45 | 3.12x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.011% / 0.045% / 0.080% | True breakout | 43.8% | 6.2% | 50.0% | 3.20x | 0.193% / -0.006% |
| 2026-02-23 10:00 | 15.68x | Bearish pin-bar / upper rejection | Flat / fading | 0.023% / 0.034% / 0.028% | Position building in range | 3.0% | 78.8% | 18.2% | 5.63x | 0.040% / 0.017% |
| 2026-02-23 12:00 | 2.60x | Full-bodied bearish | Flat / fading | 0.000% / 0.006% / 0.006% | Weak move without breakout | 80.0% | 0.0% | 20.0% | 1.51x | 0.017% / 0.017% |
| 2026-02-23 16:00 | 4.70x | Full-bodied bullish | Flat / fading | 0.000% / -0.023% / -0.023% | Position building in range | 83.3% | 16.7% | 0.0% | 5.36x | 0.017% / 0.023% |
| 2026-02-23 17:45 | 3.34x | Full-bodied bearish | Reversal | 0.006% / 0.034% / 0.045% | Liquidity sweep / reversal | 85.7% | 0.0% | 14.3% | 1.51x | 0.006% / 0.091% |
| 2026-02-23 18:15 | 10.53x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.057% / 0.011% / 0.250% | True breakout | 40.0% | 60.0% | 0.0% | 2.00x | 0.267% / 0.011% |
| 2026-02-24 07:00 | 9.28x | Full-bodied bullish | Impulse / continuation | 0.096% / 0.102% / 0.096% | True breakout | 77.5% | 7.5% | 15.0% | 5.28x | 0.232% / 0.170% |
| 2026-02-24 07:15 | 8.82x | Bearish pin-bar / upper rejection | Flat / fading | 0.006% / -0.079% / 0.023% | Weak move without breakout | 40.5% | 57.1% | 2.4% | 4.20x | 0.062% / 0.266% |
| 2026-02-24 08:00 | 4.95x | Bullish pin-bar / lower rejection | Reversal | 0.023% / -0.102% / -0.119% | Liquidity sweep / reversal | 29.2% | 2.1% | 68.8% | 3.50x | 0.062% / 0.192% |
| 2026-02-24 10:00 | 13.93x | Bullish pin-bar / lower rejection | Reversal | 0.085% / 0.272% / 0.125% | Liquidity sweep / reversal | 34.1% | 22.0% | 44.0% | 4.23x | 0.040% / 0.465% |
| 2026-02-24 10:15 | 10.62x | Bearish pin-bar / upper rejection | Flat / fading | 0.187% / 0.051% / 0.006% | Position building in range | 19.1% | 75.3% | 5.6% | 3.25x | 0.232% / 0.045% |
| 2026-02-24 10:30 | 2.65x | Full-bodied bullish | Reversal | -0.136% / -0.147% / -0.198% | Liquidity sweep / reversal | 65.3% | 16.3% | 18.4% | 1.50x | 0.000% / 0.232% |
| 2026-02-24 10:45 | 2.91x | Small-body bearish | Flat / fading | -0.011% / -0.045% / -0.119% | Weak move without breakout | 53.8% | 7.7% | 38.5% | 1.17x | 0.147% / 0.079% |
| 2026-02-24 13:15 | 2.92x | Full-bodied bearish | Flat / fading | 0.063% / 0.085% / 0.057% | Position building in range | 75.7% | 1.4% | 23.0% | 2.15x | 0.051% / 0.125% |
| 2026-02-25 07:00 | 2.87x | Bearish pin-bar / upper rejection | Flat / fading | 0.097% / 0.040% / 0.000% | Weak move without breakout | 30.0% | 43.3% | 26.7% | 4.24x | 0.103% / 0.000% |
| 2026-02-25 10:00 | 4.13x | Small-body bullish | Impulse / continuation | 0.142% / 0.051% / 0.120% | True breakout | 42.3% | 30.8% | 26.9% | 2.00x | 0.171% / 0.023% |
| 2026-02-25 10:15 | 11.06x | Full-bodied bullish | Flat / fading | -0.091% / -0.080% / -0.028% | Position building in range | 73.5% | 14.7% | 11.8% | 2.38x | 0.006% / 0.119% |
| 2026-02-25 16:15 | 3.56x | Bullish pin-bar / lower rejection | Reversal | 0.029% / 0.046% / -0.006% | Liquidity sweep / reversal | 22.2% | 33.3% | 44.4% | 1.62x | 0.017% / 0.086% |
| 2026-02-25 18:15 | 4.20x | Full-bodied bullish | Flat / fading | -0.034% / -0.137% / -0.103% | Weak move without breakout | 100.0% | 0.0% | 0.0% | 2.84x | 0.034% / 0.137% |
| 2026-02-26 07:00 | 2.79x | Small-body bullish | Flat / fading | -0.023% / -0.028% / -0.040% | Weak move without breakout | 57.1% | 28.6% | 14.3% | 1.85x | 0.000% / 0.063% |
| 2026-02-26 09:15 | 4.64x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.011% / 0.325% / 0.165% | True breakout | 40.0% | 46.7% | 13.3% | 1.78x | 0.376% / 0.023% |
| 2026-02-26 09:45 | 19.62x | Full-bodied bullish | Flat / fading | -0.125% / -0.159% / -0.136% | Position building in range | 87.0% | 13.0% | 0.0% | 7.43x | -0.011% / 0.227% |
| 2026-02-26 10:00 | 3.17x | Full-bodied bearish | Flat / fading | -0.034% / 0.006% / 0.091% | Weak move without breakout | 72.0% | 8.0% | 20.0% | 1.88x | 0.102% / 0.102% |
| 2026-02-26 17:15 | 5.66x | Full-bodied bearish | Impulse / continuation | -0.114% / -0.114% / -0.423% | True breakout | 73.1% | 2.6% | 24.4% | 5.93x | 0.509% / 0.000% |
| 2026-02-27 07:45 | 17.56x | Full-bodied bearish | Flat / fading | 0.203% / 0.185% / 0.278% | Position building in range | 95.9% | 2.7% | 1.4% | 16.20x | 0.006% / 0.290% |
| 2026-02-27 09:45 | 13.04x | Bullish pin-bar / lower rejection | Flat / fading | 0.145% / 0.197% / 0.296% | Position building in range | 41.7% | 12.5% | 45.8% | 6.02x | 0.122% / 0.331% |
| 2026-02-27 10:00 | 5.17x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.052% / 0.139% / 0.180% | True breakout | 53.1% | 6.1% | 40.8% | 1.24x | 0.272% / 0.058% |
| 2026-02-27 10:15 | 3.26x | Bearish pin-bar / upper rejection | Flat / fading | 0.087% / 0.098% / 0.081% | Weak move without breakout | 21.4% | 54.8% | 23.8% | 0.99x | 0.220% / 0.046% |
| 2026-02-27 21:00 | 3.67x | Full-bodied bullish | Flat / fading | -0.104% / -0.052% / -0.046% | Weak move without breakout | 62.5% | 18.8% | 18.7% | 1.96x | 0.110% / 0.121% |
| 2026-02-28 12:15 | 4.35x | Full-bodied bearish | Impulse / continuation | -0.070% / -0.012% / 0.122% | True breakout | 75.9% | 3.7% | 20.4% | 2.51x | 0.209% / 0.145% |
| 2026-02-28 12:30 | 3.35x | Bullish pin-bar / lower rejection | Reversal | 0.058% / 0.017% / 0.134% | Liquidity sweep / reversal | 36.8% | 0.0% | 63.2% | 1.57x | 0.128% / 0.215% |
| 2026-02-28 12:45 | 2.73x | Bullish pin-bar / lower rejection | Flat / fading | -0.041% / 0.134% / 0.035% | Weak move without breakout | 19.2% | 38.5% | 42.3% | 1.98x | 0.157% / 0.105% |
| 2026-03-01 10:15 | 4.37x | Full-bodied bullish | Impulse / continuation | 0.122% / 0.197% / 0.145% | True breakout | 69.1% | 29.6% | 1.2% | 6.67x | 0.296% / 0.012% |
| 2026-03-01 10:30 | 2.50x | Full-bodied bullish | Impulse / continuation | 0.075% / 0.064% / -0.012% | True breakout | 79.3% | 20.7% | 0.0% | 1.66x | 0.174% / 0.029% |
| 2026-03-01 17:00 | 3.16x | Full-bodied bullish | Flat / fading | -0.046% / -0.099% / -0.035% | Weak move without breakout | 64.3% | 0.0% | 35.7% | 3.27x | 0.012% / 0.128% |
| 2026-03-02 07:00 | 13.81x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.041% / 0.076% / 0.064% | True breakout | 39.6% | 60.4% | 0.0% | 3.86x | 0.186% / 0.145% |
| 2026-03-02 07:15 | 5.15x | Bullish pin-bar / lower rejection | Reversal | 0.035% / -0.070% / -0.029% | Liquidity sweep / reversal | 1.8% | 30.4% | 67.9% | 3.60x | 0.105% / 0.168% |
| 2026-03-02 08:00 | 3.36x | Full-bodied bullish | Reversal | -0.052% / -0.029% / -0.151% | Liquidity sweep / reversal | 61.3% | 9.7% | 29.0% | 1.43x | 0.029% / 0.267% |
| 2026-03-02 09:00 | 4.90x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.006% / -0.116% / -0.058% | True breakout | 55.6% | 0.0% | 44.4% | 2.03x | 0.267% / 0.064% |
| 2026-03-02 09:30 | 3.82x | Small-body bearish | Reversal | 0.064% / 0.058% / 0.384% | Liquidity sweep / reversal | 45.9% | 18.9% | 35.1% | 1.48x | 0.151% / 0.547% |
| 2026-03-02 09:45 | 3.73x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.006% / 0.349% / 0.425% | True breakout | 21.6% | 27.5% | 51.0% | 1.90x | 0.483% / 0.186% |
| 2026-03-02 10:00 | 3.17x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.355% / 0.326% / 0.454% | True breakout | 4.9% | 24.4% | 70.7% | 1.38x | 0.640% / 0.029% |
| 2026-03-02 10:15 | 6.53x | Full-bodied bullish | Flat / fading | -0.029% / 0.075% / 0.128% | Weak move without breakout | 69.7% | 25.8% | 4.5% | 2.78x | 0.284% / 0.075% |
| 2026-03-02 11:00 | 3.96x | Bearish pin-bar / upper rejection | Reversal | 0.029% / -0.052% / -0.017% | Liquidity sweep / reversal | 11.1% | 71.1% | 17.8% | 1.32x | 0.098% / 0.191% |
| 2026-03-02 17:30 | 2.82x | Full-bodied bearish | Impulse / continuation | -0.216% / -0.233% / -0.233% | True breakout | 77.8% | 7.4% | 14.8% | 1.09x | 0.437% / 0.006% |
| 2026-03-02 17:45 | 6.59x | Full-bodied bearish | Flat / fading | -0.018% / -0.035% / -0.053% | Weak move without breakout | 68.5% | 1.9% | 29.6% | 2.27x | 0.222% / 0.082% |
| 2026-03-02 18:00 | 2.77x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.018% / 0.000% / -0.356% | True breakout | 11.4% | 37.1% | 51.4% | 1.34x | 0.531% / 0.053% |
| 2026-03-03 09:00 | 3.00x | Full-bodied bearish | Impulse / continuation | -0.135% / -0.187% / -0.585% | True breakout | 96.6% | 0.0% | 3.4% | 1.37x | 0.702% / 0.029% |
| 2026-03-03 09:15 | 2.60x | Full-bodied bearish | Impulse / continuation | -0.053% / -0.387% / -0.422% | True breakout | 65.7% | 14.3% | 20.0% | 1.54x | 0.569% / 0.006% |
| 2026-03-03 09:30 | 10.92x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.334% / -0.399% / -0.270% | True breakout | 30.0% | 3.3% | 66.7% | 1.22x | 0.516% / 0.000% |
| 2026-03-03 09:45 | 5.93x | Full-bodied bearish | Flat / fading | -0.065% / -0.035% / 0.165% | Weak move without breakout | 76.0% | 0.0% | 24.0% | 2.89x | 0.182% / 0.182% |
| 2026-03-03 10:00 | 5.48x | Bullish pin-bar / lower rejection | Reversal | 0.029% / 0.130% / 0.230% | Liquidity sweep / reversal | 26.5% | 32.7% | 40.8% | 1.61x | 0.041% / 0.336% |
| 2026-03-03 12:15 | 2.77x | Full-bodied bearish | Flat / fading | -0.006% / 0.059% / -0.183% | Weak move without breakout | 63.0% | 0.0% | 37.0% | 1.29x | 0.236% / 0.100% |
| 2026-03-03 18:15 | 2.52x | Full-bodied bullish | Reversal | 0.018% / -0.095% / 0.006% | Liquidity sweep / reversal | 60.0% | 0.0% | 40.0% | 0.47x | 0.059% / 0.095% |
| 2026-03-04 07:00 | 2.54x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.124% / 0.272% / 0.277% | True breakout | 32.0% | 24.0% | 44.0% | 2.41x | 0.419% / 0.024% |
| 2026-03-04 07:15 | 2.97x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.147% / 0.153% / 0.236% | True breakout | 41.2% | 51.0% | 7.8% | 4.67x | 0.295% / -0.012% |
| 2026-03-04 07:30 | 2.66x | Bearish pin-bar / upper rejection | Flat / fading | 0.006% / 0.006% / 0.000% | Position building in range | 43.7% | 52.1% | 4.2% | 3.52x | 0.141% / 0.059% |
| 2026-03-04 10:00 | 3.67x | Bullish pin-bar / lower rejection | Reversal | 0.147% / 0.265% / 0.348% | Liquidity sweep / reversal | 34.3% | 5.7% | 60.0% | 1.51x | 0.006% / 0.484% |
| 2026-03-04 11:15 | 3.75x | Bullish pin-bar / lower rejection | Flat / fading | 0.065% / 0.041% / 0.012% | Weak move without breakout | 27.3% | 30.3% | 42.4% | 1.42x | 0.129% / 0.024% |
| 2026-03-04 11:45 | 3.04x | Small-body bearish | Flat / fading | -0.018% / -0.029% / -0.035% | Weak move without breakout | 28.6% | 35.7% | 35.7% | 0.59x | 0.088% / 0.076% |
| 2026-03-04 16:15 | 3.25x | Full-bodied bearish | Impulse / continuation | -0.047% / -0.083% / -0.489% | True breakout | 74.2% | 0.0% | 25.8% | 4.05x | 0.554% / 0.065% |
| 2026-03-04 17:15 | 4.25x | Full-bodied bearish | Impulse / continuation | -0.195% / -0.154% / 0.024% | True breakout | 83.3% | 0.0% | 16.7% | 3.10x | 0.320% / 0.148% |
| 2026-03-04 17:30 | 2.97x | Small-body bearish | Reversal | 0.042% / 0.113% / 0.202% | Liquidity sweep / reversal | 51.6% | 15.6% | 32.8% | 2.54x | 0.071% / 0.344% |
| 2026-03-05 07:00 | 5.37x | Small-body bullish | Flat / fading | 0.012% / -0.024% / -0.053% | Position building in range | 51.9% | 23.4% | 24.7% | 4.71x | 0.088% / 0.147% |
| 2026-03-05 12:30 | 10.81x | Full-bodied bullish | Impulse / continuation | 0.041% / -0.018% / 0.230% | True breakout | 76.9% | 11.0% | 12.1% | 3.85x | 0.253% / 0.035% |
| 2026-03-05 14:45 | 2.82x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.105% / -0.094% | Liquidity sweep / reversal | 56.0% | 44.0% | 0.0% | 1.92x | 0.076% / 0.234% |
| 2026-03-06 10:00 | 3.10x | Doji / upper rejection | Impulse / continuation | -0.059% / -0.041% / 0.170% | True breakout | 0.0% | 69.2% | 30.8% | 0.79x | 0.240% / 0.240% |
| 2026-03-06 10:45 | 2.91x | Full-bodied bullish | Impulse / continuation | 0.105% / 0.053% / -0.076% | True breakout | 72.0% | 8.0% | 20.0% | 1.61x | 0.176% / 0.123% |
| 2026-03-06 11:00 | 5.89x | Full-bodied bullish | Reversal | -0.053% / -0.064% / -0.246% | Liquidity sweep / reversal | 61.3% | 38.7% | 0.0% | 1.92x | 0.006% / 0.292% |
| 2026-03-06 12:45 | 4.27x | Small-body bearish | Impulse / continuation | -0.094% / -0.035% / -0.265% | True breakout | 54.8% | 16.1% | 29.0% | 3.36x | 0.288% / 0.012% |
| 2026-03-06 13:45 | 2.36x | Full-bodied bearish | Impulse / continuation | 0.059% / -0.041% / -0.242% | True breakout | 85.4% | 4.9% | 9.8% | 1.72x | 0.289% / 0.106% |
| 2026-03-06 23:30 | 2.70x | Bearish pin-bar / upper rejection | Reversal | -0.030% / -0.030% / -0.521% | Liquidity sweep / reversal | 18.2% | 45.5% | 36.4% | 1.13x | 0.178% / 8.520% |
| 2026-03-09 07:00 | 7.88x | Bullish pin-bar / lower rejection | Reversal | -0.255% / 0.267% / 0.386% | Liquidity sweep / reversal | 3.5% | 1.6% | 94.9% | 175.78x | 1.739% / 0.392% |
| 2026-03-09 07:30 | 5.59x | Bullish pin-bar / lower rejection | Flat / fading | -0.065% / 0.118% / 0.308% | Weak move without breakout | 18.1% | 5.8% | 76.0% | 3.08x | 0.361% / 0.213% |
| 2026-03-09 08:45 | 2.53x | Bullish pin-bar / lower rejection | Flat / fading | -0.414% / -0.331% / -0.307% | Weak move without breakout | 36.6% | 22.0% | 41.5% | 0.28x | 0.496% / 0.000% |
| 2026-03-09 09:00 | 5.56x | Full-bodied bearish | Flat / fading | 0.083% / 0.036% / 0.350% | Position building in range | 83.3% | 0.0% | 16.7% | 0.56x | 0.042% / 0.356% |
| 2026-03-09 16:30 | 2.97x | Bearish pin-bar / upper rejection | Reversal | -0.035% / -0.035% / -0.148% | Liquidity sweep / reversal | 8.0% | 80.0% | 12.0% | 1.69x | 0.041% / 0.195% |
| 2026-03-09 18:15 | 4.22x | Full-bodied bullish | Impulse / continuation | 0.159% / 0.153% / 0.201% | True breakout | 91.4% | 0.0% | 8.6% | 1.99x | 0.460% / 0.000% |
| 2026-03-09 18:30 | 4.66x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.006% / 0.230% / -0.094% | True breakout | 60.0% | 40.0% | 0.0% | 2.32x | 0.300% / 0.194% |
| 2026-03-09 19:00 | 4.55x | Full-bodied bullish | Reversal | -0.188% / -0.323% / -0.270% | Liquidity sweep / reversal | 78.2% | 21.8% | 0.0% | 2.57x | 0.012% / 0.423% |
| 2026-03-09 22:30 | 5.09x | Full-bodied bullish | Impulse / continuation | 0.323% / 0.382% / 0.646% | True breakout | 65.3% | 31.4% | 3.3% | 4.62x | 0.652% / 0.047% |
| 2026-03-09 22:45 | 2.89x | Full-bodied bullish | Impulse / continuation | 0.059% / -0.012% / 0.445% | True breakout | 82.6% | 8.7% | 8.7% | 2.23x | 0.451% / 0.088% |
| 2026-03-10 07:00 | 3.00x | Small-body bearish | Reversal | 0.357% / 0.135% / 0.246% | Liquidity sweep / reversal | 44.6% | 33.8% | 21.5% | 3.35x | 0.070% / 0.374% |
| 2026-03-10 15:45 | 3.51x | Full-bodied bearish | Impulse / continuation | -0.175% / -0.368% / -0.380% | True breakout | 93.9% | 1.5% | 4.5% | 2.67x | 0.421% / -0.006% |
| 2026-03-10 19:45 | 4.09x | Full-bodied bearish | Flat / fading | 0.047% / 0.154% / 0.213% | Weak move without breakout | 88.4% | 4.7% | 7.0% | 3.34x | 0.225% / 0.314% |
| 2026-03-10 20:00 | 4.03x | Bullish pin-bar / lower rejection | Flat / fading | 0.107% / 0.237% / 0.284% | Weak move without breakout | 13.1% | 24.6% | 62.3% | 1.39x | 0.284% / 0.095% |
| 2026-03-11 09:45 | 2.87x | Bearish pin-bar / upper rejection | Flat / fading | -0.018% / 0.018% / 0.065% | Weak move without breakout | 24.4% | 58.5% | 17.1% | 2.05x | 0.094% / 0.130% |
| 2026-03-11 12:00 | 3.78x | Full-bodied bearish | Impulse / continuation | -0.035% / -0.024% / -0.207% | True breakout | 66.7% | 9.8% | 23.5% | 2.40x | 0.218% / 0.041% |
| 2026-03-11 12:45 | 4.00x | Full-bodied bearish | Flat / fading | -0.012% / 0.071% / -0.041% | Weak move without breakout | 96.7% | 3.3% | 0.0% | 1.30x | 0.118% / 0.095% |
| 2026-03-11 17:45 | 2.85x | Bearish pin-bar / upper rejection | Reversal | -0.036% / 0.036% / -0.047% | Liquidity sweep / reversal | 3.3% | 50.0% | 46.7% | 1.65x | 0.083% / 0.077% |
| 2026-03-11 23:15 | 2.60x | Full-bodied bullish | Impulse / continuation | 0.006% / 0.042% / 0.024% | True breakout | 60.0% | 20.0% | 20.0% | 3.21x | 0.101% / 0.136% |
| 2026-03-12 07:00 | 2.75x | Bullish pin-bar / lower rejection | Flat / fading | -0.059% / 0.024% / -0.130% | Weak move without breakout | 12.5% | 20.0% | 67.5% | 3.68x | 0.202% / 0.113% |
| 2026-03-12 07:15 | 2.72x | Bearish pin-bar / upper rejection | Reversal | 0.083% / -0.101% / 0.036% | Liquidity sweep / reversal | 24.4% | 46.3% | 29.3% | 3.10x | 0.142% / 0.089% |
| 2026-03-12 10:00 | 11.10x | Small-body bullish | Flat / fading | 0.136% / 0.089% / 0.059% | Weak move without breakout | 53.4% | 39.7% | 6.9% | 3.09x | 0.213% / 0.024% |
| 2026-03-12 10:15 | 3.54x | Full-bodied bullish | Flat / fading | -0.047% / -0.035% / -0.100% | Weak move without breakout | 92.6% | 0.0% | 7.4% | 1.24x | 0.077% / 0.142% |
| 2026-03-12 17:15 | 2.72x | Full-bodied bullish | Reversal | -0.207% / -0.342% / -0.431% | Liquidity sweep / reversal | 83.7% | 16.3% | 0.0% | 2.27x | 0.106% / 0.449% |
| 2026-03-13 08:30 | 3.81x | Full-bodied bullish | Flat / fading | -0.035% / -0.177% / -0.212% | Weak move without breakout | 86.7% | 11.7% | 1.7% | 3.84x | 0.065% / 0.253% |
| 2026-03-13 08:45 | 2.66x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.141% / -0.165% / -0.053% | True breakout | 52.9% | 47.1% | 0.0% | 0.90x | 0.218% / 0.018% |
| 2026-03-13 09:00 | 3.58x | Full-bodied bearish | Reversal | -0.024% / -0.035% / 0.389% | Liquidity sweep / reversal | 80.0% | 10.0% | 10.0% | 1.52x | 0.077% / 0.543% |
| 2026-03-13 10:00 | 11.06x | Full-bodied bullish | Flat / fading | -0.018% / 0.000% / 0.047% | Position building in range | 65.8% | 32.9% | 1.3% | 3.64x | 0.100% / 0.094% |
| 2026-03-13 10:15 | 4.15x | Bullish pin-bar / lower rejection | Reversal | 0.018% / 0.035% / 0.264% | Liquidity sweep / reversal | 7.7% | 42.3% | 50.0% | 0.99x | 0.012% / 0.335% |
| 2026-03-13 11:15 | 3.25x | Full-bodied bullish | Flat / fading | -0.141% / -0.141% / -0.135% | Position building in range | 66.7% | 23.5% | 9.8% | 2.01x | 0.006% / 0.176% |
| 2026-03-13 15:30 | 2.90x | Full-bodied bearish | Impulse / continuation | -0.006% / -0.053% / -0.024% | True breakout | 89.3% | 3.6% | 7.1% | 1.55x | 0.153% / 0.006% |
| 2026-03-13 20:30 | 3.63x | Bullish pin-bar / lower rejection | Flat / fading | -0.071% / -0.053% / -0.024% | Weak move without breakout | 57.9% | 0.0% | 42.1% | 1.56x | 0.095% / 0.000% |
| 2026-03-14 17:45 | 3.57x | Full-bodied bullish | Flat / fading | 0.000% / 0.006% / 0.018% | Weak move without breakout | 87.5% | 0.0% | 12.5% | 1.75x | 0.024% / 0.018% |
| 2026-03-14 18:45 | 3.24x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.071% / 0.112% | True breakout | 83.3% | 16.7% | 0.0% | 1.65x | 0.171% / 0.000% |
| 2026-03-15 10:00 | 3.83x | Bearish pin-bar / upper rejection | Flat / fading | 0.065% / 0.041% / 0.012% | Position building in range | 24.1% | 58.6% | 17.2% | 8.12x | 0.071% / 0.000% |
| 2026-03-15 10:15 | 6.15x | Full-bodied bullish | Flat / fading | -0.024% / -0.035% / -0.030% | Weak move without breakout | 100.0% | 0.0% | 0.0% | 2.17x | 0.006% / 0.059% |
| 2026-03-15 10:30 | 3.28x | Full-bodied bearish | Impulse / continuation | -0.012% / -0.030% / 0.006% | True breakout | 80.0% | 20.0% | 0.0% | 0.90x | 0.035% / 0.035% |
| 2026-03-15 17:45 | 7.65x | Bearish pin-bar / upper rejection | Reversal | 0.024% / 0.012% / 0.154% | Liquidity sweep / reversal | 42.9% | 42.9% | 14.3% | 1.56x | 0.000% / 0.165% |
| 2026-03-15 18:00 | 4.23x | Bullish pin-bar / lower rejection | Reversal | -0.012% / 0.047% / 0.307% | Liquidity sweep / reversal | 20.0% | 20.0% | 60.0% | 1.09x | 0.024% / 0.307% |
| 2026-03-15 18:30 | 4.62x | Small-body bullish | Impulse / continuation | 0.083% / 0.260% / 0.395% | True breakout | 60.0% | 20.0% | 20.0% | 2.96x | 0.460% / 0.000% |
| 2026-03-15 18:45 | 3.19x | Full-bodied bullish | Impulse / continuation | 0.177% / 0.348% / 0.271% | True breakout | 68.7% | 12.5% | 18.8% | 2.70x | 0.377% / -0.159% |
| 2026-03-16 07:00 | 23.81x | Full-bodied bullish | Flat / fading | -0.035% / -0.076% / -0.100% | Position building in range | 75.7% | 13.5% | 10.8% | 4.28x | 0.000% / 0.141% |
| 2026-03-16 09:00 | 5.61x | Full-bodied bearish | Reversal | -0.035% / 0.012% / 0.159% | Liquidity sweep / reversal | 80.0% | 0.0% | 20.0% | 2.10x | 0.065% / 0.165% |
| 2026-03-16 10:00 | 4.64x | Full-bodied bullish | Impulse / continuation | -0.006% / -0.170% / -0.141% | True breakout | 86.8% | 2.6% | 10.5% | 2.27x | 0.188% / 0.259% |
| 2026-03-16 10:15 | 6.41x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.165% / -0.129% / -0.182% | True breakout | 2.3% | 72.7% | 25.0% | 2.41x | 0.253% / 0.006% |
| 2026-03-16 10:30 | 4.33x | Full-bodied bearish | Flat / fading | 0.035% / 0.029% / -0.012% | Position building in range | 63.6% | 2.3% | 34.1% | 2.28x | 0.065% / 0.118% |
| 2026-03-16 15:45 | 3.28x | Full-bodied bearish | Impulse / continuation | -0.006% / -0.095% / -0.148% | True breakout | 95.7% | 0.0% | 4.3% | 1.71x | 0.231% / 0.041% |
| 2026-03-16 19:00 | 2.53x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / 0.006% / -0.041% | Position building in range | 2.8% | 36.1% | 61.1% | 1.86x | 0.059% / 0.059% |
| 2026-03-17 07:00 | 7.81x | Full-bodied bullish | Impulse / continuation | -0.030% / -0.035% / -0.024% | True breakout | 74.2% | 0.0% | 25.8% | 5.05x | 0.041% / 0.059% |
| 2026-03-17 09:15 | 3.86x | Full-bodied bearish | Flat / fading | 0.018% / -0.012% / -0.035% | Weak move without breakout | 66.7% | 4.8% | 28.6% | 1.87x | 0.100% / 0.018% |
| 2026-03-17 14:30 | 5.63x | Full-bodied bearish | Flat / fading | 0.107% / 0.030% / 0.047% | Weak move without breakout | 65.9% | 0.0% | 34.1% | 3.59x | 0.125% / 0.148% |
| 2026-03-17 16:00 | 8.77x | Bullish pin-bar / lower rejection | Flat / fading | 0.048% / -0.024% / 0.006% | Position building in range | 56.1% | 2.3% | 41.7% | 7.80x | 0.125% / 0.191% |
| 2026-03-17 16:15 | 3.19x | Bullish pin-bar / lower rejection | Reversal | -0.071% / 0.065% / 0.012% | Liquidity sweep / reversal | 33.3% | 3.3% | 63.3% | 1.20x | 0.143% / 0.143% |
| 2026-03-17 16:30 | 3.03x | Bullish pin-bar / lower rejection | Reversal | 0.137% / 0.030% / 0.024% | Liquidity sweep / reversal | 48.0% | 4.0% | 48.0% | 0.94x | 0.131% / 0.214% |
| 2026-03-17 16:45 | 3.18x | Full-bodied bullish | Reversal | -0.107% / -0.054% / -0.184% | Liquidity sweep / reversal | 71.4% | 17.9% | 10.7% | 1.03x | 0.077% / 0.268% |
| 2026-03-18 07:00 | 4.96x | Full-bodied bearish | Flat / fading | 0.078% / 0.048% / 0.149% | Position building in range | 61.9% | 2.4% | 35.7% | 4.90x | 0.036% / 0.155% |
| 2026-03-18 09:00 | 2.66x | Bullish pin-bar / lower rejection | Reversal | 0.006% / 0.060% / 0.119% | Liquidity sweep / reversal | 16.7% | 0.0% | 83.3% | 1.25x | 0.054% / 0.232% |
| 2026-03-18 09:45 | 11.94x | Full-bodied bullish | Impulse / continuation | -0.065% / 0.137% / 0.291% | True breakout | 71.4% | 28.6% | 0.0% | 1.84x | 0.375% / 0.095% |
| 2026-03-18 10:00 | 3.10x | Small-body bearish | Reversal | 0.202% / 0.321% / 0.268% | Liquidity sweep / reversal | 55.6% | 16.7% | 27.8% | 1.11x | -0.012% / 0.440% |
| 2026-03-18 10:15 | 5.16x | Full-bodied bullish | Impulse / continuation | 0.119% / 0.154% / 0.048% | True breakout | 65.3% | 34.7% | 0.0% | 2.96x | 0.238% / 0.036% |
| 2026-03-18 10:30 | 2.66x | Bearish pin-bar / upper rejection | Flat / fading | 0.036% / -0.053% / 0.006% | Weak move without breakout | 50.0% | 50.0% | 0.0% | 2.05x | 0.095% / 0.154% |
| 2026-03-18 11:30 | 2.90x | Bearish pin-bar / upper rejection | Flat / fading | -0.071% / -0.030% / 0.000% | Weak move without breakout | 51.7% | 44.8% | 3.4% | 1.38x | 0.030% / 0.113% |
| 2026-03-18 16:00 | 2.60x | Full-bodied bearish | Impulse / continuation | -0.298% / -0.322% / -0.334% | True breakout | 64.7% | 2.9% | 32.4% | 1.55x | 0.519% / 0.006% |
| 2026-03-18 16:15 | 3.30x | Full-bodied bearish | Impulse / continuation | -0.024% / -0.173% / -0.078% | True breakout | 86.4% | 0.0% | 13.6% | 2.55x | 0.221% / 0.090% |
| 2026-03-18 22:45 | 2.74x | Doji | Impulse / continuation | -0.018% / -0.042% / 0.000% | True breakout | 0.0% | 50.0% | 50.0% | 0.63x | 0.102% / 0.102% |
| 2026-03-18 23:30 | 2.67x | Bearish pin-bar / upper rejection | Reversal | 0.048% / 0.174% / 0.299% | Liquidity sweep / reversal | 4.5% | 54.5% | 40.9% | 1.81x | 0.030% / 0.425% |
| 2026-03-19 09:00 | 3.03x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.096% / -0.185% | True breakout | 69.0% | 0.0% | 31.0% | 1.71x | 0.298% / 0.113% |
| 2026-03-19 10:00 | 9.19x | Small-body bearish | Reversal | 0.167% / 0.114% / 0.305% | Liquidity sweep / reversal | 37.7% | 34.8% | 27.5% | 3.72x | 0.048% / 0.419% |
| 2026-03-19 10:15 | 4.62x | Full-bodied bullish | Impulse / continuation | -0.054% / -0.060% / 0.179% | True breakout | 82.4% | 14.7% | 2.9% | 1.51x | 0.251% / 0.215% |
| 2026-03-19 10:30 | 2.54x | Bearish pin-bar / upper rejection | Reversal | -0.006% / 0.191% / 0.036% | Liquidity sweep / reversal | 37.5% | 45.8% | 16.7% | 1.02x | 0.161% / 0.305% |
| 2026-03-19 10:45 | 3.34x | Bullish pin-bar / lower rejection | Reversal | 0.197% / 0.239% / 0.114% | Liquidity sweep / reversal | 6.1% | 15.2% | 78.8% | 1.48x | 0.030% / 0.311% |
| 2026-03-19 11:00 | 2.61x | Small-body bullish | Flat / fading | 0.042% / -0.155% / -0.173% | Weak move without breakout | 57.9% | 33.3% | 8.8% | 2.54x | 0.083% / 0.233% |
| 2026-03-19 15:45 | 2.34x | Small-body bearish | Impulse / continuation | 0.096% / -0.090% / -0.336% | True breakout | 42.2% | 33.3% | 24.4% | 1.52x | 0.354% / 0.150% |
| 2026-03-19 17:00 | 2.41x | Small-body bearish | Reversal | 0.169% / 0.223% / 0.380% | Liquidity sweep / reversal | 52.5% | 16.4% | 31.1% | 1.81x | 0.084% / 0.591% |
| 2026-03-19 17:15 | 2.64x | Small-body bullish | Impulse / continuation | 0.054% / 0.271% / 0.193% | True breakout | 43.7% | 34.4% | 21.9% | 1.73x | 0.422% / 0.018% |
| 2026-03-20 09:00 | 2.84x | Full-bodied bullish | Impulse / continuation | 0.072% / 0.102% / 0.054% | True breakout | 77.4% | 6.5% | 16.1% | 1.94x | 0.197% / 0.006% |
| 2026-03-20 09:15 | 2.86x | Full-bodied bullish | Impulse / continuation | 0.030% / -0.006% / 0.132% | True breakout | 61.1% | 27.8% | 11.1% | 1.05x | 0.143% / 0.060% |
| 2026-03-20 09:30 | 2.50x | Small-body bullish | Reversal | -0.036% / -0.048% / 0.532% | Liquidity sweep / reversal | 50.0% | 25.0% | 25.0% | 0.45x | 1.704% / 0.090% |
| 2026-03-20 10:00 | 2.74x | Bearish pin-bar / upper rejection | Reversal | 0.150% / 0.580% / 0.736% | Liquidity sweep / reversal | 6.5% | 71.0% | 22.6% | 1.90x | 0.012% / 1.752% |
| 2026-03-20 10:15 | 3.52x | Full-bodied bullish | Impulse / continuation | 0.430% / 0.597% / 0.502% | True breakout | 82.8% | 6.9% | 10.3% | 1.70x | 1.600% / 0.012% |
| 2026-03-20 10:30 | 18.09x | Bearish pin-bar / upper rejection | Flat / fading | 0.166% / 0.155% / 0.113% | Position building in range | 26.3% | 72.6% | 1.1% | 14.88x | 0.309% / 0.042% |
| 2026-03-20 10:45 | 3.28x | Bearish pin-bar / upper rejection | Flat / fading | -0.012% / -0.095% / 0.208% | Weak move without breakout | 49.2% | 40.7% | 10.2% | 1.65x | 0.237% / 0.142% |
| 2026-03-20 13:30 | 5.13x | Full-bodied bearish | Flat / fading | 0.203% / 0.113% / 0.084% | Weak move without breakout | 62.4% | 33.3% | 4.2% | 3.13x | 0.096% / 0.346% |
| 2026-03-20 23:30 | 3.43x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.078% / 0.150% / 0.042% | True breakout | 52.0% | 0.0% | 48.0% | 2.67x | 0.288% / 0.180% |
| 2026-03-23 07:00 | 4.83x | Full-bodied bearish | Impulse -> reversal | 0.102% / 0.234% / 0.426% | False breakout | 60.3% | 39.7% | 0.0% | 4.75x | 0.120% / 0.432% |
| 2026-03-23 07:15 | 4.14x | Small-body bullish | Impulse / continuation | 0.132% / 0.102% / 0.384% | True breakout | 30.2% | 30.2% | 39.6% | 3.31x | 0.384% / 0.000% |
| 2026-03-23 09:30 | 2.74x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.144% / -0.072% / -0.006% | True breakout | 31.0% | 17.2% | 51.7% | 1.05x | 0.300% / 0.078% |
| 2026-03-23 09:45 | 6.22x | Bullish pin-bar / lower rejection | Reversal | 0.072% / 0.006% / 0.282% | Liquidity sweep / reversal | 48.1% | 3.7% | 48.1% | 1.86x | 0.042% / 0.390% |
| 2026-03-23 10:00 | 2.65x | Small-body bullish | Impulse / continuation | -0.066% / 0.066% / 0.186% | True breakout | 44.4% | 29.6% | 25.9% | 0.87x | 0.318% / 0.102% |
| 2026-03-23 10:45 | 5.47x | Bullish pin-bar / lower rejection | Reversal | -0.024% / -0.240% / -0.144% | Liquidity sweep / reversal | 32.4% | 26.5% | 41.2% | 2.19x | 0.048% / 0.329% |
| 2026-03-23 13:15 | 2.33x | Full-bodied bearish | Impulse / continuation | -0.350% / -0.507% / -0.157% | True breakout | 89.1% | 7.3% | 3.6% | 1.66x | 0.966% / 0.109% |
| 2026-03-23 13:30 | 4.29x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.158% / 0.194% / 0.424% | False breakout | 54.8% | 3.8% | 41.3% | 3.14x | 0.618% / 0.485% |
| 2026-03-23 14:00 | 5.29x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / 0.230% / 0.115% | Weak move without breakout | 33.1% | 24.7% | 42.1% | 4.56x | 0.290% / 0.139% |
| 2026-03-24 08:30 | 3.27x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.115% / 0.000% | Liquidity sweep / reversal | 37.5% | 62.5% | 0.0% | 0.79x | 0.036% / 0.115% |
| 2026-03-24 09:00 | 2.51x | Full-bodied bearish | Flat / fading | 0.072% / 0.115% / 0.109% | Weak move without breakout | 95.0% | 5.0% | 0.0% | 1.02x | 0.000% / 0.133% |
| 2026-03-24 10:15 | 12.10x | Full-bodied bullish | Impulse / continuation | 0.102% / 0.198% / 0.595% | True breakout | 82.4% | 14.9% | 2.7% | 4.73x | 0.649% / 0.018% |
| 2026-03-24 10:30 | 2.98x | Small-body bullish | Impulse / continuation | 0.096% / 0.330% / 0.463% | True breakout | 51.5% | 39.4% | 9.1% | 1.76x | 0.547% / 0.030% |
| 2026-03-24 10:45 | 3.67x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.234% / 0.396% / 0.504% | True breakout | 34.8% | 54.3% | 10.9% | 2.65x | 0.618% / 0.012% |
| 2026-03-24 11:00 | 3.41x | Full-bodied bullish | Impulse / continuation | 0.162% / 0.132% / 0.168% | True breakout | 67.9% | 22.6% | 9.4% | 2.69x | 0.383% / 0.018% |
| 2026-03-24 11:15 | 2.73x | Full-bodied bullish | Impulse / continuation | -0.030% / 0.108% / 0.167% | True breakout | 66.7% | 23.1% | 10.3% | 1.71x | 0.221% / 0.066% |
| 2026-03-24 11:45 | 2.95x | Bearish pin-bar / upper rejection | Reversal | -0.102% / 0.060% / -0.227% | Liquidity sweep / reversal | 54.8% | 45.2% | 0.0% | 1.64x | 0.173% / 0.287% |
| 2026-03-24 12:45 | 2.62x | Full-bodied bearish | Flat / fading | -0.090% / -0.006% / -0.138% | Weak move without breakout | 80.0% | 3.3% | 16.7% | 1.90x | 0.186% / 0.084% |
| 2026-03-24 15:00 | 2.32x | Small-body bearish | Impulse / continuation | -0.102% / -0.221% / -0.377% | True breakout | 52.7% | 34.5% | 12.7% | 1.77x | 0.401% / 0.024% |
| 2026-03-24 22:45 | 7.29x | Full-bodied bullish | Flat / fading | -0.060% / -0.204% / -0.066% | Weak move without breakout | 81.8% | 11.4% | 6.8% | 6.42x | 0.012% / 0.264% |
| 2026-03-24 23:15 | 3.36x | Full-bodied bearish | Reversal | 0.072% / 0.138% / 0.150% | Liquidity sweep / reversal | 68.6% | 2.9% | 28.6% | 3.45x | 0.012% / 0.234% |
| 2026-03-25 07:00 | 3.21x | Bearish pin-bar / upper rejection | Reversal | -0.012% / 0.258% / 0.348% | Liquidity sweep / reversal | 20.0% | 50.0% | 30.0% | 1.51x | 0.096% / 0.348% |
| 2026-03-25 12:00 | 4.33x | Bullish pin-bar / lower rejection | Flat / fading | -0.024% / 0.072% / 0.114% | Position building in range | 38.1% | 14.3% | 47.6% | 2.99x | 0.096% / 0.169% |
| 2026-03-25 15:30 | 3.21x | Bearish pin-bar / upper rejection | Reversal | -0.060% / -0.024% / -0.054% | Liquidity sweep / reversal | 10.5% | 63.2% | 26.3% | 1.01x | 0.012% / 0.174% |
| 2026-03-25 23:30 | 2.51x | Bearish pin-bar / upper rejection | Reversal | 0.030% / 0.084% / 0.048% | Liquidity sweep / reversal | 9.1% | 45.5% | 45.5% | 1.13x | 0.030% / 0.144% |
| 2026-03-26 07:00 | 7.16x | Small-body bearish | Reversal | 0.012% / 0.108% / 0.042% | Liquidity sweep / reversal | 28.6% | 32.1% | 39.3% | 2.67x | 0.036% / 0.108% |
| 2026-03-26 09:00 | 3.35x | Full-bodied bullish | Flat / fading | 0.024% / -0.030% / -0.102% | Weak move without breakout | 94.4% | 5.6% | 0.0% | 1.49x | 0.060% / 0.150% |
| 2026-03-26 09:15 | 4.96x | Bearish pin-bar / upper rejection | Reversal | -0.054% / -0.036% / -0.192% | Liquidity sweep / reversal | 26.7% | 40.0% | 33.3% | 1.14x | 0.012% / 0.240% |
| 2026-03-26 10:00 | 3.74x | Small-body bearish | Impulse / continuation | -0.066% / -0.060% / -0.258% | True breakout | 50.0% | 21.4% | 28.6% | 2.04x | 0.270% / 0.000% |
| 2026-03-26 10:15 | 2.63x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.006% / -0.084% / -0.252% | True breakout | 52.6% | 5.3% | 42.1% | 1.24x | 0.282% / 0.024% |
| 2026-03-26 10:30 | 2.73x | Bullish pin-bar / lower rejection | Reversal | -0.090% / -0.198% / -0.349% | Liquidity sweep / reversal | 16.7% | 25.0% | 58.3% | 0.75x | 0.000% / 0.403% |
| 2026-03-26 10:45 | 6.46x | Full-bodied bearish | Impulse / continuation | -0.108% / -0.168% / -0.337% | True breakout | 60.0% | 0.0% | 40.0% | 1.68x | 0.367% / 0.048% |
| 2026-03-26 11:15 | 3.18x | Small-body bearish | Impulse -> reversal | -0.090% / -0.169% / 0.018% | False breakout | 47.6% | 28.6% | 23.8% | 1.32x | 0.199% / 0.133% |
| 2026-03-26 11:45 | 2.60x | Bearish pin-bar / upper rejection | Reversal | 0.290% / 0.187% / 0.109% | Liquidity sweep / reversal | 37.1% | 48.6% | 14.3% | 2.09x | 0.018% / 0.302% |
| 2026-03-26 18:30 | 2.85x | Bullish pin-bar / lower rejection | Reversal | -0.078% / -0.223% / -0.181% | Liquidity sweep / reversal | 44.0% | 4.0% | 52.0% | 2.85x | 0.054% / 0.289% |
| 2026-03-27 07:00 | 2.92x | Small-body bullish | Reversal | -0.054% / -0.103% / -0.121% | Liquidity sweep / reversal | 54.5% | 13.6% | 31.8% | 1.87x | 0.000% / 0.169% |
| 2026-03-27 08:45 | 3.48x | Full-bodied bearish | Reversal | 0.024% / 0.036% / 0.145% | Liquidity sweep / reversal | 70.8% | 12.5% | 16.7% | 1.83x | 0.018% / 0.242% |
| 2026-03-27 09:00 | 2.52x | Bearish pin-bar / upper rejection | Reversal | 0.012% / 0.157% / 0.170% | Liquidity sweep / reversal | 8.3% | 62.5% | 29.2% | 1.69x | 0.042% / 0.218% |
| 2026-03-27 09:45 | 2.57x | Bearish pin-bar / upper rejection | Reversal | 0.048% / 0.127% / 0.024% | Liquidity sweep / reversal | 25.0% | 41.7% | 33.3% | 1.35x | 0.079% / 0.242% |
| 2026-03-27 10:15 | 3.60x | Bearish pin-bar / upper rejection | Reversal | 0.072% / -0.103% / -0.254% | Liquidity sweep / reversal | 40.6% | 59.4% | 0.0% | 1.85x | 0.091% / 0.290% |
| 2026-03-27 10:30 | 3.82x | Bullish pin-bar / lower rejection | Reversal | -0.175% / -0.314% / -0.447% | Liquidity sweep / reversal | 27.9% | 2.3% | 69.8% | 2.35x | 0.018% / 0.592% |
| 2026-03-27 11:00 | 3.98x | Full-bodied bearish | Impulse / continuation | -0.012% / -0.133% / -0.157% | True breakout | 84.0% | 16.0% | 0.0% | 1.18x | 0.279% / 0.079% |
| 2026-03-27 11:30 | 2.97x | Bullish pin-bar / lower rejection | Flat / fading | -0.097% / -0.024% / -0.115% | Position building in range | 42.6% | 6.4% | 51.1% | 2.03x | 0.133% / 0.036% |
| 2026-03-27 13:00 | 3.91x | Full-bodied bearish | Impulse / continuation | -0.055% / -0.336% / -0.024% | True breakout | 86.9% | 3.6% | 9.5% | 2.87x | 0.440% / 0.055% |
| 2026-03-27 19:30 | 5.49x | Small-body bearish | Flat / fading | -0.111% / 0.018% / 0.080% | Position building in range | 44.0% | 17.3% | 38.7% | 3.12x | 0.123% / 0.154% |
| 2026-03-28 11:30 | 2.97x | Full-bodied bearish | Flat / fading | 0.056% / 0.050% / 0.180% | Position building in range | 86.0% | 0.0% | 14.0% | 2.69x | 0.012% / 0.186% |
| 2026-03-28 18:00 | 2.66x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.000% / -0.093% / -0.050% | True breakout | 36.4% | 18.2% | 45.5% | 1.88x | 0.112% / 0.006% |
| 2026-03-28 18:30 | 3.46x | Full-bodied bearish | Flat / fading | 0.019% / 0.043% / 0.025% | Weak move without breakout | 83.3% | 0.0% | 16.7% | 3.32x | 0.012% / 0.130% |
| 2026-03-29 17:15 | 3.11x | Full-bodied bullish | Flat / fading | -0.012% / -0.068% / 0.019% | Weak move without breakout | 66.7% | 19.0% | 14.3% | 3.34x | 0.037% / 0.068% |
| 2026-03-30 07:00 | 12.57x | Full-bodied bullish | Impulse / continuation | 0.136% / 0.148% / 0.068% | True breakout | 78.3% | 19.6% | 2.2% | 4.21x | 0.209% / 0.111% |
| 2026-03-30 07:15 | 4.19x | Bullish pin-bar / lower rejection | Flat / fading | 0.012% / 0.037% / 0.031% | Position building in range | 36.5% | 23.1% | 40.4% | 3.87x | 0.055% / 0.105% |
| 2026-03-30 09:00 | 4.27x | Full-bodied bearish | Impulse / continuation | -0.006% / -0.055% / -0.382% | True breakout | 80.4% | 0.0% | 19.6% | 2.74x | 0.388% / 0.018% |
| 2026-03-30 09:45 | 6.22x | Full-bodied bearish | Impulse / continuation | -0.111% / -0.130% / -0.359% | True breakout | 63.6% | 7.3% | 29.1% | 2.42x | 0.359% / 0.093% |
| 2026-03-30 10:00 | 2.51x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.019% / -0.105% / -0.241% | True breakout | 47.1% | 50.0% | 2.9% | 1.29x | 0.371% / 0.080% |
| 2026-03-30 11:00 | 2.85x | Doji / lower rejection | Impulse / continuation | -0.099% / -0.124% / 0.161% | True breakout | 0.0% | 19.2% | 80.8% | 1.05x | 0.217% / 0.217% |
| 2026-03-30 11:15 | 2.39x | Full-bodied bearish | Reversal | -0.025% / 0.093% / 0.509% | Liquidity sweep / reversal | 66.7% | 16.7% | 16.7% | 1.16x | 0.118% / 0.559% |
| 2026-03-30 12:00 | 4.56x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.248% / 0.322% / 0.180% | True breakout | 47.4% | 8.8% | 43.9% | 1.93x | 0.564% / 0.099% |
| 2026-03-30 12:15 | 4.65x | Full-bodied bullish | Impulse / continuation | 0.074% / -0.025% / -0.025% | True breakout | 62.5% | 12.5% | 25.0% | 1.94x | 0.315% / 0.204% |
| 2026-03-30 12:30 | 2.85x | Bearish pin-bar / upper rejection | Reversal | -0.099% / -0.142% / 0.136% | Liquidity sweep / reversal | 25.0% | 75.0% | 0.0% | 1.43x | 0.222% / 0.278% |
| 2026-03-30 17:00 | 3.02x | Full-bodied bearish | Reversal | 0.495% / 0.570% / 1.014% | Liquidity sweep / reversal | 80.8% | 4.8% | 14.4% | 3.01x | 0.063% / 1.058% |
| 2026-03-30 17:15 | 2.46x | Full-bodied bullish | Impulse / continuation | 0.075% / 0.237% / 0.374% | True breakout | 71.8% | 19.1% | 9.1% | 2.89x | 0.598% / 0.006% |
| 2026-03-31 07:00 | 4.57x | Small-body bearish | Flat / fading | -0.056% / -0.068% / 0.006% | Weak move without breakout | 41.2% | 29.4% | 29.4% | 3.42x | 0.105% / 0.056% |
| 2026-03-31 07:15 | 3.01x | Bearish pin-bar / upper rejection | Reversal | -0.012% / 0.081% / 0.099% | Liquidity sweep / reversal | 47.4% | 47.4% | 5.3% | 1.60x | 0.050% / 0.099% |
| 2026-03-31 09:15 | 3.88x | Full-bodied bullish | Impulse / continuation | -0.049% / -0.056% / 0.062% | True breakout | 72.7% | 9.1% | 18.2% | 3.42x | 0.111% / 0.328% |
| 2026-03-31 10:00 | 3.52x | Bullish pin-bar / lower rejection | Reversal | 0.242% / 0.328% / 0.322% | Liquidity sweep / reversal | 46.8% | 2.1% | 51.1% | 2.58x | 0.149% / 0.384% |
| 2026-03-31 10:15 | 5.82x | Small-body bullish | Impulse / continuation | 0.087% / -0.093% / 0.291% | True breakout | 54.9% | 11.3% | 33.8% | 3.34x | 0.408% / 0.105% |
| 2026-03-31 10:30 | 5.62x | Small-body bullish | Reversal | -0.179% / -0.006% / 0.179% | Liquidity sweep / reversal | 46.2% | 34.6% | 19.2% | 1.07x | 0.321% / 0.192% |
| 2026-03-31 11:00 | 2.76x | Full-bodied bullish | Impulse / continuation | 0.210% / 0.185% / 0.958% | True breakout | 80.6% | 16.7% | 2.8% | 1.47x | 0.982% / 0.068% |
| 2026-03-31 11:15 | 4.87x | Small-body bullish | Impulse / continuation | -0.025% / 0.210% / 0.647% | True breakout | 54.7% | 29.7% | 15.6% | 2.47x | 0.845% / 0.043% |
| 2026-03-31 11:45 | 4.09x | Full-bodied bullish | Impulse / continuation | 0.535% / 0.437% / 0.714% | True breakout | 100.0% | 0.0% | 0.0% | 1.29x | 0.744% / 0.025% |
| 2026-03-31 12:00 | 5.87x | Full-bodied bullish | Impulse / continuation | -0.098% / 0.092% / 0.373% | True breakout | 91.6% | 4.2% | 4.2% | 2.93x | 0.557% / 0.190% |
| 2026-03-31 12:15 | 3.03x | Bearish pin-bar / upper rejection | Reversal | 0.190% / 0.276% / 0.576% | Liquidity sweep / reversal | 36.1% | 52.8% | 11.1% | 0.93x | 0.092% / 0.655% |
| 2026-04-01 07:00 | 5.00x | Small-body bullish | Impulse / continuation | -0.037% / 0.154% / -0.025% | True breakout | 52.9% | 15.7% | 31.4% | 4.61x | 0.161% / 0.086% |
| 2026-04-01 07:30 | 2.77x | Full-bodied bullish | Flat / fading | -0.148% / -0.179% / -0.154% | Weak move without breakout | 93.9% | 0.0% | 6.1% | 2.30x | 0.006% / 0.240% |
| 2026-04-01 10:00 | 7.17x | Full-bodied bullish | Impulse / continuation | 0.092% / -0.068% / -0.239% | True breakout | 98.2% | 0.0% | 1.8% | 5.99x | 0.141% / 0.246% |
| 2026-04-01 10:15 | 3.75x | Bullish pin-bar / lower rejection | Reversal | -0.159% / -0.270% / -0.288% | Liquidity sweep / reversal | 25.9% | 14.8% | 59.3% | 2.18x | 0.043% / 0.337% |
| 2026-04-02 07:00 | 3.90x | Small-body bearish | Impulse / continuation | -0.129% / -0.074% / -0.136% | True breakout | 50.0% | 20.8% | 29.2% | 3.52x | 0.314% / 0.006% |
| 2026-04-02 09:00 | 3.51x | Full-bodied bearish | Impulse / continuation | 0.074% / 0.068% / -0.099% | True breakout | 100.0% | 0.0% | 0.0% | 1.47x | 0.161% / 0.093% |
| 2026-04-02 10:00 | 4.50x | Full-bodied bearish | Reversal | 0.081% / 0.074% / 0.328% | Liquidity sweep / reversal | 70.3% | 2.7% | 27.0% | 1.97x | 0.006% / 0.347% |
| 2026-04-02 11:00 | 3.04x | Full-bodied bullish | Flat / fading | -0.049% / 0.056% / -0.228% | Weak move without breakout | 91.3% | 6.5% | 2.2% | 2.36x | 0.062% / 0.278% |
| 2026-04-02 15:00 | 2.12x | Doji / upper rejection | Impulse / continuation | -0.099% / -0.136% / 0.148% | True breakout | 0.0% | 77.1% | 22.9% | 1.98x | 0.722% / 0.722% |
| 2026-04-02 15:45 | 6.18x | Bullish pin-bar / lower rejection | Reversal | 0.539% / 0.489% / 0.533% | Liquidity sweep / reversal | 43.2% | 0.0% | 56.8% | 3.74x | -0.012% / 0.849% |
| 2026-04-02 16:00 | 2.49x | Full-bodied bullish | Impulse / continuation | -0.049% / 0.111% / 0.123% | True breakout | 92.4% | 7.6% | 0.0% | 3.00x | 0.308% / 0.092% |
| 2026-04-02 16:45 | 2.81x | Bearish pin-bar / upper rejection | Reversal | 0.129% / 0.074% / 0.031% | Liquidity sweep / reversal | 37.3% | 62.7% | 0.0% | 1.45x | 0.074% / 0.179% |
| 2026-04-02 23:00 | 3.18x | Full-bodied bearish | Flat / fading | -0.043% / 0.043% / 0.123% | Weak move without breakout | 78.7% | 0.0% | 21.3% | 6.09x | 0.074% / 0.130% |
| 2026-04-03 07:00 | 4.54x | Full-bodied bullish | Impulse / continuation | 0.277% / 0.117% / 0.289% | True breakout | 81.6% | 18.4% | 0.0% | 2.83x | 0.339% / 0.049% |
| 2026-04-03 07:15 | 4.30x | Full-bodied bullish | Flat / fading | -0.160% / -0.025% / -0.061% | Weak move without breakout | 84.9% | 0.0% | 15.1% | 3.55x | 0.061% / 0.160% |
| 2026-04-03 09:00 | 5.93x | Full-bodied bullish | Reversal | -0.184% / -0.313% / -0.386% | Liquidity sweep / reversal | 70.9% | 18.2% | 10.9% | 2.37x | 0.025% / 0.423% |
| 2026-04-03 09:15 | 3.91x | Full-bodied bearish | Impulse / continuation | -0.129% / -0.129% / -0.473% | True breakout | 75.0% | 10.0% | 15.0% | 1.49x | 0.522% / 0.018% |
| 2026-04-03 10:15 | 5.03x | Full-bodied bearish | Impulse / continuation | 0.080% / -0.142% / 0.056% | True breakout | 84.3% | 0.0% | 15.7% | 1.75x | 0.296% / 0.228% |
| 2026-04-03 11:00 | 3.37x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.136% / -0.167% / -0.377% | False breakout | 18.8% | 27.1% | 54.2% | 1.62x | 0.309% / 0.408% |
| 2026-04-03 11:15 | 3.05x | Bearish pin-bar / upper rejection | Reversal | -0.302% / -0.314% / -0.567% | Liquidity sweep / reversal | 42.3% | 53.8% | 3.8% | 1.66x | 0.173% / 0.635% |
| 2026-04-03 11:30 | 3.75x | Small-body bearish | Impulse / continuation | -0.012% / -0.210% / -0.216% | True breakout | 57.8% | 34.9% | 7.2% | 2.50x | 0.334% / 0.124% |
| 2026-04-03 16:15 | 2.46x | Full-bodied bearish | Impulse / continuation | 0.062% / -0.069% / -0.069% | True breakout | 83.6% | 10.9% | 5.5% | 2.67x | 0.168% / 0.112% |
| 2026-04-04 14:45 | 4.20x | Small-body bearish | Flat / fading | -0.006% / 0.006% / 0.000% | Weak move without breakout | 33.3% | 33.3% | 33.3% | 0.71x | 0.012% / 0.019% |
| 2026-04-04 16:45 | 7.11x | Full-bodied bearish | Flat / fading | 0.006% / -0.006% / 0.025% | Weak move without breakout | 80.0% | 0.0% | 20.0% | 1.56x | 0.006% / 0.031% |
| 2026-04-05 10:15 | 12.26x | Full-bodied bullish | Flat / fading | -0.037% / -0.050% / -0.062% | Position building in range | 61.2% | 38.8% | 0.0% | 9.66x | 0.025% / 0.087% |
| 2026-04-05 17:30 | 4.88x | Bullish pin-bar / lower rejection | Reversal | 0.000% / -0.025% / -0.019% | Liquidity sweep / reversal | 8.3% | 16.7% | 75.0% | 2.55x | 0.000% / 0.044% |
| 2026-04-05 18:45 | 4.74x | Full-bodied bearish | Reversal | 0.162% / 0.373% / 0.317% | Liquidity sweep / reversal | 81.8% | 0.0% | 18.2% | 1.88x | -0.162% / 0.504% |
| 2026-04-06 07:00 | 30.31x | Small-body bullish | Flat / fading | -0.037% / -0.056% / -0.081% | Position building in range | 52.7% | 38.2% | 9.1% | 7.40x | 0.012% / 0.124% |
| 2026-04-06 07:15 | 3.56x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.019% / -0.074% / -0.248% | True breakout | 22.7% | 13.6% | 63.6% | 2.05x | 0.335% / 0.019% |
| 2026-04-06 07:30 | 2.59x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.056% / -0.025% / -0.217% | True breakout | 23.1% | 23.1% | 53.8% | 1.10x | 0.316% / 0.019% |
| 2026-04-06 08:15 | 5.22x | Full-bodied bearish | Impulse / continuation | 0.012% / 0.106% / -0.099% | True breakout | 67.4% | 2.2% | 30.4% | 3.48x | 0.174% / 0.131% |
| 2026-04-06 09:00 | 3.22x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.174% / -0.162% / -0.155% | True breakout | 23.8% | 4.8% | 71.4% | 1.22x | 0.249% / 0.000% |
| 2026-04-06 09:15 | 4.08x | Full-bodied bearish | Flat / fading | 0.012% / 0.025% / -0.050% | Position building in range | 70.0% | 0.0% | 30.0% | 2.19x | 0.050% / 0.118% |
| 2026-04-06 10:45 | 4.36x | Full-bodied bearish | Flat / fading | -0.050% / -0.075% / -0.069% | Position building in range | 63.3% | 4.1% | 32.7% | 2.49x | 0.093% / 0.019% |
| 2026-04-06 12:15 | 4.33x | Full-bodied bullish | Flat / fading | -0.068% / 0.037% / 0.050% | Weak move without breakout | 67.7% | 32.3% | 0.0% | 1.57x | 0.093% / 0.068% |
| 2026-04-06 14:45 | 3.92x | Full-bodied bearish | Flat / fading | 0.044% / 0.087% / 0.062% | Weak move without breakout | 70.0% | 17.5% | 12.5% | 2.50x | 0.006% / 0.225% |
| 2026-04-07 08:45 | 8.10x | Bullish pin-bar / lower rejection | Flat / fading | -0.050% / -0.093% / -0.112% | Position building in range | 34.5% | 4.6% | 60.9% | 4.89x | 0.162% / 0.025% |
| 2026-04-07 10:00 | 2.54x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.287% / 0.356% / 0.630% | True breakout | 26.5% | 67.6% | 5.9% | 1.68x | 0.680% / 0.012% |
| 2026-04-07 10:45 | 5.96x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.186% / 0.553% / 0.255% | True breakout | 26.9% | 73.1% | 0.0% | 2.17x | 0.695% / 0.019% |
| 2026-04-07 11:15 | 3.34x | Full-bodied bullish | Flat / fading | -0.124% / -0.296% / -0.296% | Position building in range | 62.1% | 24.2% | 13.7% | 3.61x | 0.136% / 0.420% |
| 2026-04-07 14:30 | 2.71x | Full-bodied bearish | Impulse / continuation | -0.162% / -0.062% / -0.150% | True breakout | 76.7% | 17.8% | 5.6% | 2.90x | 0.250% / 0.150% |
| 2026-04-07 14:45 | 2.99x | Full-bodied bearish | Flat / fading | 0.100% / 0.006% / 0.131% | Weak move without breakout | 66.7% | 0.0% | 33.3% | 1.20x | 0.075% / 0.313% |
| 2026-04-07 16:15 | 2.87x | Small-body bullish | Reversal | -0.169% / -0.156% / -0.213% | Liquidity sweep / reversal | 28.8% | 31.8% | 39.4% | 1.98x | 0.006% / 0.250% |
| 2026-04-07 21:00 | 3.02x | Bullish pin-bar / lower rejection | Flat / fading | 0.050% / 0.031% / 0.019% | Position building in range | 50.0% | 2.4% | 47.6% | 2.28x | 0.082% / 0.100% |
| 2026-04-08 07:00 | 4.72x | Bearish pin-bar / upper rejection | Flat / fading | 0.206% / 0.181% / 0.169% | Weak move without breakout | 7.7% | 53.8% | 38.5% | 2.92x | 0.344% / 0.094% |
| 2026-04-08 07:30 | 2.75x | Bearish pin-bar / upper rejection | Reversal | -0.212% / -0.012% / 0.081% | Liquidity sweep / reversal | 7.3% | 63.4% | 29.3% | 1.53x | 0.125% / 0.275% |
| 2026-04-08 23:30 | 3.71x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.025% / 0.100% / 0.113% | True breakout | 15.0% | 40.0% | 45.0% | 2.48x | 0.194% / 0.050% |
| 2026-04-09 09:15 | 3.82x | Bullish pin-bar / lower rejection | Flat / fading | -0.056% / 0.006% / 0.094% | Weak move without breakout | 56.2% | 3.1% | 40.6% | 2.32x | 0.113% / 0.169% |
| 2026-04-09 10:45 | 2.46x | Full-bodied bullish | Flat / fading | -0.119% / -0.119% / -0.119% | Weak move without breakout | 96.8% | 0.0% | 3.2% | 1.77x | 0.031% / 0.175% |
| 2026-04-09 16:00 | 2.45x | Full-bodied bearish | Flat / fading | 0.038% / 0.063% / 0.056% | Position building in range | 77.5% | 10.0% | 12.5% | 2.64x | 0.025% / 0.100% |
| 2026-04-09 19:00 | 2.35x | Bullish pin-bar / lower rejection | Flat / fading | -0.031% / -0.038% / -0.094% | Weak move without breakout | 47.9% | 0.0% | 52.1% | 3.04x | 0.183% / 0.006% |
| 2026-04-09 22:00 | 5.81x | Full-bodied bullish | Flat / fading | 0.069% / 0.000% / -0.013% | Weak move without breakout | 70.8% | 29.2% | 0.0% | 5.72x | 0.214% / 0.126% |
| 2026-04-10 07:00 | 3.37x | Full-bodied bullish | Flat / fading | -0.044% / -0.125% / -0.044% | Position building in range | 74.3% | 17.1% | 8.6% | 3.49x | 0.038% / 0.156% |
| 2026-04-10 10:30 | 2.53x | Full-bodied bearish | Impulse / continuation | -0.321% / -0.378% / -0.195% | True breakout | 61.1% | 2.8% | 36.1% | 1.73x | 0.384% / 0.019% |
| 2026-04-10 10:45 | 5.35x | Full-bodied bearish | Flat / fading | -0.057% / -0.019% / 0.183% | Weak move without breakout | 91.4% | 1.7% | 6.9% | 3.16x | 0.063% / 0.284% |
| 2026-04-10 11:00 | 2.54x | Bearish pin-bar / upper rejection | Reversal | 0.038% / 0.183% / 0.348% | Liquidity sweep / reversal | 52.9% | 41.2% | 5.9% | 0.80x | 0.000% / 0.379% |
| 2026-04-10 13:15 | 3.12x | Full-bodied bullish | Impulse / continuation | 0.025% / 0.232% / 0.433% | True breakout | 95.2% | 4.8% | 0.0% | 0.77x | 0.446% / 0.019% |
| 2026-04-10 13:45 | 5.00x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.056% / 0.200% / 0.351% | True breakout | 55.4% | 44.6% | 0.0% | 2.35x | 0.451% / 0.000% |
| 2026-04-10 14:30 | 2.63x | Bearish pin-bar / upper rejection | Reversal | 0.037% / -0.131% / -0.119% | Liquidity sweep / reversal | 42.5% | 55.0% | 2.5% | 1.42x | 0.119% / 0.150% |
| 2026-04-10 18:00 | 3.07x | Full-bodied bearish | Flat / fading | -0.031% / 0.031% / 0.252% | Weak move without breakout | 76.4% | 12.7% | 10.9% | 2.05x | 0.088% / 0.302% |
| 2026-04-17 09:45 | 40.16x | Doji | Impulse / continuation | 1.832% / 1.869% / 2.124% | True breakout | 0.0% | 0.0% | 0.0% | 0.00x | 2.561% / 2.561% |
| 2026-04-17 10:00 | 110.20x | Full-bodied bullish | Flat / fading | 0.037% / 0.251% / 0.196% | Position building in range | 67.9% | 32.1% | 0.0% | 14.08x | 0.545% / 0.122% |
| 2026-04-17 10:15 | 4.91x | Bearish pin-bar / upper rejection | Reversal | 0.214% / 0.251% / -0.073% | Liquidity sweep / reversal | 12.9% | 62.9% | 24.3% | 1.29x | 0.508% / 0.128% |
| 2026-04-17 10:30 | 4.33x | Full-bodied bullish | Reversal | 0.037% / -0.055% / -0.140% | Liquidity sweep / reversal | 85.4% | 12.2% | 2.4% | 0.71x | 0.293% / 0.482% |
| 2026-04-17 10:45 | 3.47x | Bullish pin-bar / lower rejection | Reversal | -0.092% / -0.323% / -0.390% | Liquidity sweep / reversal | 26.1% | 26.1% | 47.8% | 0.39x | 0.256% / 0.519% |
| 2026-04-17 11:00 | 3.64x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.232% / -0.085% / -0.354% | True breakout | 23.8% | 66.7% | 9.5% | 1.06x | 0.434% / 0.067% |
| 2026-04-19 11:30 | 2.86x | Full-bodied bullish | Flat / fading | 0.061% / 0.049% / 0.049% | Weak move without breakout | 81.2% | 18.8% | 0.0% | 2.06x | 0.061% / 0.018% |
| 2026-04-19 14:30 | 4.54x | Full-bodied bullish | Flat / fading | 0.043% / 0.031% / 0.025% | Weak move without breakout | 78.9% | 15.8% | 5.3% | 2.35x | 0.043% / 0.074% |
| 2026-04-19 14:45 | 2.99x | Bullish pin-bar / lower rejection | Flat / fading | -0.012% / -0.037% / -0.018% | Position building in range | 36.8% | 0.0% | 63.2% | 2.09x | 0.000% / 0.067% |
| 2026-04-19 18:45 | 2.60x | Small-body bullish | Impulse / continuation | 0.061% / 0.178% / 0.184% | True breakout | 40.0% | 26.7% | 33.3% | 2.53x | 0.288% / -0.061% |
| 2026-04-20 07:00 | 10.64x | Bearish pin-bar / upper rejection | Flat / fading | -0.012% / 0.006% / 0.024% | Position building in range | 48.6% | 48.6% | 2.7% | 5.76x | 0.086% / 0.086% |
| 2026-04-20 08:45 | 3.22x | Bullish pin-bar / lower rejection | Reversal | -0.202% / -0.245% / -0.306% | Liquidity sweep / reversal | 26.3% | 0.0% | 73.7% | 1.62x | 0.000% / 0.379% |
| 2026-04-20 09:00 | 2.85x | Full-bodied bearish | Impulse / continuation | -0.043% / -0.031% / 0.031% | True breakout | 94.1% | 2.9% | 2.9% | 2.69x | 0.178% / 0.067% |
| 2026-04-20 09:15 | 4.96x | Bullish pin-bar / lower rejection | Reversal | 0.012% / -0.061% / -0.135% | Liquidity sweep / reversal | 23.1% | 11.5% | 65.4% | 1.78x | 0.319% / 0.110% |
| 2026-04-20 10:15 | 4.39x | Bullish pin-bar / lower rejection | Flat / fading | -0.006% / -0.098% / 0.000% | Position building in range | 53.1% | 0.0% | 46.9% | 3.01x | 0.166% / 0.068% |
| 2026-04-20 15:45 | 2.73x | Full-bodied bearish | Flat / fading | 0.006% / -0.074% / 0.000% | Weak move without breakout | 66.7% | 0.0% | 33.3% | 1.79x | 0.080% / 0.062% |
| 2026-04-20 17:15 | 5.12x | Bearish pin-bar / upper rejection | Reversal | 0.222% / 0.173% / 0.154% | Liquidity sweep / reversal | 30.0% | 55.0% | 15.0% | 1.15x | 0.000% / 0.271% |
| 2026-04-20 17:30 | 4.37x | Full-bodied bullish | Impulse / continuation | -0.049% / -0.012% / 0.117% | True breakout | 100.0% | 0.0% | 0.0% | 2.08x | 0.148% / 0.123% |
| 2026-04-20 18:30 | 3.10x | Full-bodied bullish | Flat / fading | -0.031% / 0.031% / 0.018% | Weak move without breakout | 83.3% | 13.9% | 2.8% | 1.76x | 0.080% / 0.037% |
| 2026-04-21 07:00 | 3.37x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.062% / -0.018% | True breakout | 97.1% | 0.0% | 2.9% | 3.19x | 0.098% / 0.074% |
| 2026-04-21 07:45 | 2.85x | Full-bodied bullish | Reversal | -0.074% / -0.049% / -0.111% | Liquidity sweep / reversal | 75.0% | 15.0% | 10.0% | 1.63x | 0.000% / 0.117% |
| 2026-04-21 10:15 | 3.19x | Full-bodied bullish | Reversal | -0.037% / -0.031% / -0.172% | Liquidity sweep / reversal | 74.1% | 25.9% | 0.0% | 1.96x | 0.006% / 0.178% |
| 2026-04-21 14:00 | 5.37x | Full-bodied bullish | Flat / fading | -0.104% / -0.068% / -0.141% | Position building in range | 86.0% | 2.0% | 12.0% | 3.38x | 0.006% / 0.178% |
| 2026-04-21 14:45 | 2.41x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.068% / -0.332% / -0.522% | True breakout | 3.6% | 42.9% | 53.6% | 1.57x | 0.645% / 0.006% |
| 2026-04-21 15:15 | 3.44x | Full-bodied bearish | Impulse / continuation | 0.031% / -0.191% / -0.351% | True breakout | 82.7% | 3.8% | 13.5% | 2.74x | 0.388% / 0.099% |
| 2026-04-21 15:45 | 2.55x | Full-bodied bearish | Impulse / continuation | -0.049% / -0.161% / -0.191% | True breakout | 64.9% | 0.0% | 35.1% | 2.74x | 0.259% / 0.031% |
| 2026-04-21 17:15 | 4.49x | Full-bodied bullish | Flat / fading | -0.019% / 0.074% / 0.049% | Position building in range | 62.5% | 33.0% | 4.5% | 3.13x | 0.148% / 0.068% |
| 2026-04-21 22:45 | 3.01x | Full-bodied bearish | Impulse / continuation | 0.099% / 0.012% / 0.037% | True breakout | 79.4% | 0.0% | 20.6% | 2.75x | 0.210% / 0.099% |
| 2026-04-21 23:15 | 3.47x | Bullish pin-bar / lower rejection | Reversal | 0.056% / 0.025% / 0.012% | Liquidity sweep / reversal | 28.0% | 0.0% | 72.0% | 3.47x | 0.124% / 0.130% |
| 2026-04-22 07:30 | 19.31x | Bullish pin-bar / lower rejection | Reversal | 0.516% / 0.516% / 0.516% | Liquidity sweep / reversal | 34.5% | 3.1% | 62.4% | 14.32x | 0.044% / 0.535% |
| 2026-04-22 07:45 | 5.05x | Full-bodied bullish | Flat / fading | 0.000% / -0.161% / -0.043% | Position building in range | 90.3% | 3.2% | 6.5% | 2.94x | 0.019% / 0.396% |
| 2026-04-22 10:15 | 2.62x | Small-body bullish | Flat / fading | 0.025% / 0.043% / 0.080% | Position building in range | 57.3% | 37.1% | 5.6% | 2.12x | 0.093% / 0.019% |
| 2026-04-22 17:30 | 3.68x | Full-bodied bullish | Impulse / continuation | 0.147% / 0.153% / 0.172% | True breakout | 76.9% | 23.1% | 0.0% | 2.18x | 0.208% / 0.018% |
| 2026-04-22 17:45 | 2.74x | Full-bodied bullish | Flat / fading | 0.006% / 0.024% / -0.049% | Weak move without breakout | 67.6% | 20.6% | 11.8% | 1.78x | 0.061% / 0.049% |
| 2026-04-23 07:00 | 4.07x | Bearish pin-bar / upper rejection | Flat / fading | 0.110% / 0.000% / 0.202% | Position building in range | 18.6% | 81.4% | 0.0% | 4.39x | 0.214% / 0.031% |
| 2026-04-23 08:15 | 3.05x | Small-body bullish | Flat / fading | -0.049% / -0.012% / -0.055% | Weak move without breakout | 55.6% | 38.9% | 5.6% | 1.08x | 0.006% / 0.085% |
| 2026-04-23 10:45 | 2.71x | Full-bodied bearish | Impulse / continuation | 0.012% / -0.018% / -0.202% | True breakout | 89.7% | 0.0% | 10.3% | 1.95x | 0.244% / 0.061% |
| 2026-04-23 13:00 | 2.53x | Full-bodied bearish | Flat / fading | 0.061% / 0.031% / 0.074% | Position building in range | 92.1% | 0.0% | 7.9% | 2.47x | 0.006% / 0.117% |
| 2026-04-23 15:15 | 3.28x | Small-body bearish | Reversal | 0.221% / 0.190% / 0.245% | Liquidity sweep / reversal | 56.4% | 25.6% | 17.9% | 2.38x | 0.006% / 0.288% |
| 2026-04-23 18:15 | 2.70x | Bullish pin-bar / lower rejection | Reversal | 0.116% / 0.177% / 0.037% | Liquidity sweep / reversal | 52.0% | 4.0% | 44.0% | 1.39x | 0.043% / 0.177% |
| 2026-04-24 10:15 | 2.54x | Small-body bearish | Impulse / continuation | -0.037% / -0.061% / -0.135% | True breakout | 50.0% | 14.3% | 35.7% | 2.61x | 0.184% / 0.073% |
| 2026-04-24 10:45 | 2.84x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.061% / -0.073% / -0.190% | True breakout | 30.8% | 61.5% | 7.7% | 1.07x | 0.196% / 0.031% |
| 2026-04-24 11:45 | 3.09x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.037% / -0.043% / -0.031% | True breakout | 42.3% | 53.8% | 3.8% | 1.98x | 0.159% / 0.092% |
| 2026-04-24 12:00 | 6.54x | Bullish pin-bar / lower rejection | Reversal | -0.006% / 0.061% / 0.080% | Liquidity sweep / reversal | 19.2% | 3.8% | 76.9% | 1.80x | 0.049% / 0.129% |
| 2026-04-24 12:15 | 2.63x | Bearish pin-bar / upper rejection | Reversal | 0.067% / 0.012% / 0.153% | Liquidity sweep / reversal | 3.4% | 72.4% | 24.1% | 1.85x | 0.025% / 0.221% |
| 2026-04-24 13:30 | 21.99x | Full-bodied bearish | Flat / fading | -0.037% / -0.037% / -0.093% | Position building in range | 68.7% | 3.4% | 27.9% | 9.01x | 0.216% / 0.037% |
| 2026-04-24 15:15 | 3.86x | Full-bodied bearish | Impulse / continuation | -0.069% / -0.255% / -0.424% | True breakout | 75.0% | 1.0% | 24.0% | 2.73x | 0.436% / 0.000% |
| 2026-04-25 17:45 | 8.31x | Small-body bearish | Flat / fading | 0.000% / 0.000% / -0.012% | Weak move without breakout | 57.1% | 14.3% | 28.6% | 2.09x | 0.031% / 0.000% |
| 2026-04-26 12:45 | 10.53x | Full-bodied bearish | Impulse / continuation | -0.044% / -0.050% / -0.012% | True breakout | 68.7% | 0.0% | 31.3% | 3.61x | 0.069% / 0.000% |
| 2026-04-26 13:30 | 2.89x | Bullish pin-bar / lower rejection | Flat / fading | 0.012% / 0.006% / 0.000% | Weak move without breakout | 42.9% | 0.0% | 57.1% | 1.24x | 0.025% / 0.019% |
| 2026-04-26 15:30 | 4.02x | Full-bodied bearish | Flat / fading | -0.006% / 0.012% / 0.019% | Position building in range | 60.0% | 0.0% | 40.0% | 1.87x | 0.025% / 0.019% |
| 2026-04-26 17:30 | 3.52x | Doji / lower rejection | Flat / fading | -0.006% / -0.006% / -0.044% | Position building in range | 0.0% | 7.1% | 92.9% | 2.97x | 0.062% / 0.062% |
| 2026-04-26 18:30 | 3.13x | Small-body bearish | Reversal | 0.031% / 0.044% / 0.012% | Liquidity sweep / reversal | 37.5% | 25.0% | 37.5% | 1.56x | 0.050% / 0.050% |
| 2026-04-26 18:45 | 4.66x | Bullish pin-bar / lower rejection | Reversal | 0.012% / -0.012% / -0.031% | Liquidity sweep / reversal | 28.6% | 14.3% | 57.1% | 1.29x | 0.019% / 0.081% |
| 2026-04-27 07:00 | 13.55x | Bullish pin-bar / lower rejection | Reversal | -0.006% / -0.019% / 0.075% | Liquidity sweep / reversal | 25.0% | 6.2% | 68.7% | 3.11x | 0.025% / 0.087% |
| 2026-04-27 07:30 | 3.11x | Bearish pin-bar / upper rejection | Reversal | 0.056% / 0.094% / 0.387% | Liquidity sweep / reversal | 33.3% | 50.0% | 16.7% | 0.97x | 0.006% / 0.462% |
| 2026-04-27 08:30 | 11.22x | Full-bodied bullish | Reversal | -0.125% / -0.591% / -0.591% | Liquidity sweep / reversal | 77.8% | 22.2% | 0.0% | 7.00x | 0.000% / 0.859% |
| 2026-04-27 09:00 | 14.94x | Full-bodied bearish | Flat / fading | -0.094% / 0.000% / 0.063% | Position building in range | 62.5% | 1.7% | 35.8% | 10.06x | 0.113% / 0.244% |
| 2026-04-27 09:15 | 3.08x | Bearish pin-bar / upper rejection | Reversal | 0.094% / 0.100% / 0.295% | Liquidity sweep / reversal | 28.1% | 66.7% | 5.3% | 2.83x | 0.000% / 0.313% |
| 2026-04-27 15:00 | 3.12x | Bullish pin-bar / lower rejection | Flat / fading | 0.013% / 0.019% / -0.106% | Weak move without breakout | 57.6% | 0.0% | 42.4% | 2.05x | 0.063% / 0.125% |
| 2026-04-27 20:30 | 3.70x | Full-bodied bearish | Flat / fading | -0.006% / 0.000% / 0.044% | Position building in range | 63.6% | 0.0% | 36.4% | 3.60x | 0.044% / 0.063% |
| 2026-04-28 07:00 | 3.27x | Full-bodied bullish | Flat / fading | -0.013% / -0.031% / -0.031% | Position building in range | 64.4% | 15.6% | 20.0% | 3.41x | 0.006% / 0.075% |
| 2026-04-28 09:00 | 4.62x | Bearish pin-bar / upper rejection | Reversal | -0.050% / -0.220% / -0.258% | Liquidity sweep / reversal | 8.6% | 54.3% | 37.1% | 2.08x | 0.748% / 0.415% |
| 2026-04-28 09:30 | 8.32x | Bullish pin-bar / lower rejection | Flat / fading | -0.069% / -0.038% / -0.214% | Weak move without breakout | 37.9% | 8.6% | 53.4% | 3.36x | 0.239% / 0.970% |
| 2026-04-28 09:45 | 3.18x | Bullish pin-bar / lower rejection | Flat / fading | 0.032% / -0.151% / -0.069% | Weak move without breakout | 47.8% | 0.0% | 52.2% | 1.11x | 0.170% / 1.040% |
| 2026-04-28 10:00 | 8.05x | Bearish pin-bar / upper rejection | Reversal | -0.183% / -0.176% / -0.132% | Liquidity sweep / reversal | 2.9% | 91.4% | 5.7% | 8.31x | 0.000% / 0.202% |
| 2026-04-28 11:15 | 2.83x | Bearish pin-bar / upper rejection | Reversal | 0.050% / -0.107% / -0.549% | Liquidity sweep / reversal | 37.0% | 40.7% | 22.2% | 0.85x | 0.139% / 0.845% |
| 2026-04-28 12:00 | 4.43x | Full-bodied bearish | Flat / fading | 0.165% / 0.095% / -0.013% | Position building in range | 82.1% | 0.0% | 17.9% | 3.24x | 0.102% / 0.311% |
| 2026-04-28 16:45 | 4.72x | Small-body bearish | Flat / fading | 0.039% / 0.276% / 0.231% | Position building in range | 59.2% | 7.8% | 33.0% | 3.28x | 0.058% / 0.347% |
| 2026-04-29 07:00 | 2.69x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.039% / 0.064% / 0.064% | True breakout | 45.2% | 2.4% | 52.4% | 2.35x | 0.186% / 0.077% |
| 2026-04-29 10:15 | 8.17x | Full-bodied bearish | Flat / fading | 0.052% / 0.052% / 0.058% | Weak move without breakout | 72.0% | 1.0% | 27.0% | 4.24x | 0.232% / 0.207% |
| 2026-04-29 10:30 | 6.16x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.123% / 0.271% | Liquidity sweep / reversal | 21.6% | 64.9% | 13.5% | 1.25x | 0.355% / 0.284% |
| 2026-04-29 10:45 | 4.49x | Bullish pin-bar / lower rejection | Reversal | -0.123% / 0.006% / 0.716% | Liquidity sweep / reversal | 1.9% | 18.5% | 79.6% | 1.84x | 0.748% / 0.187% |
| 2026-04-29 11:45 | 2.67x | Full-bodied bullish | Impulse / continuation | -0.102% / 0.192% / 0.058% | True breakout | 93.2% | 6.8% | 0.0% | 2.20x | 0.468% / 0.179% |
| 2026-04-29 15:30 | 2.11x | Full-bodied bearish | Impulse / continuation | 0.091% / -0.526% / -0.578% | True breakout | 68.6% | 8.6% | 22.9% | 1.65x | 0.637% / 0.214% |
| 2026-04-29 16:00 | 3.58x | Full-bodied bearish | Impulse / continuation | 0.229% / -0.052% / -0.392% | True breakout | 90.7% | 0.0% | 9.3% | 2.37x | 0.849% / 0.346% |
| 2026-04-29 16:15 | 2.66x | Small-body bullish | Reversal | -0.280% / -0.730% / -0.652% | Liquidity sweep / reversal | 58.1% | 16.1% | 25.8% | 1.25x | 0.117% / 1.075% |
| 2026-04-29 16:45 | 3.66x | Full-bodied bearish | Reversal | 0.112% / 0.079% / 0.276% | Liquidity sweep / reversal | 66.3% | 12.5% | 21.2% | 1.99x | 0.348% / 0.781% |
| 2026-04-29 17:30 | 2.36x | Small-body bullish | Reversal | -0.216% / -0.457% / -0.379% | Liquidity sweep / reversal | 53.8% | 37.6% | 8.5% | 1.98x | 0.085% / 0.581% |
| 2026-04-30 09:00 | 2.86x | Full-bodied bearish | Reversal | 0.184% / 0.223% / 0.762% | Liquidity sweep / reversal | 65.7% | 22.4% | 11.9% | 2.35x | 0.000% / 0.769% |
| 2026-04-30 10:15 | 5.05x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.013% / 0.436% / 0.007% | True breakout | 50.0% | 50.0% | 0.0% | 1.63x | 0.495% / 0.124% |
| 2026-04-30 10:45 | 3.69x | Full-bodied bullish | Reversal | -0.071% / -0.428% / -0.674% | Liquidity sweep / reversal | 74.7% | 10.3% | 14.9% | 2.08x | 0.006% / 0.764% |
| 2026-04-30 20:30 | 3.29x | Bearish pin-bar / upper rejection | Flat / fading | 0.072% / 0.052% / -0.013% | Position building in range | 12.1% | 78.8% | 9.1% | 1.80x | 0.131% / 0.026% |
| 2026-05-01 17:00 | 3.11x | Full-bodied bearish | Impulse / continuation | 0.000% / -0.020% / -0.013% | True breakout | 73.3% | 13.3% | 13.3% | 3.18x | 0.164% / 0.144% |
| 2026-05-01 17:15 | 15.22x | Bullish pin-bar / lower rejection | Reversal | -0.020% / -0.020% / -0.013% | Liquidity sweep / reversal | 2.1% | 46.8% | 51.1% | 8.66x | 0.013% / 0.124% |
| 2026-05-02 10:00 | 2.84x | Bullish pin-bar / lower rejection | Reversal | -0.013% / 0.052% / 0.007% | Liquidity sweep / reversal | 6.2% | 0.0% | 93.8% | 1.44x | 0.066% / 0.026% |
| 2026-05-02 13:00 | 2.83x | Full-bodied bearish | Flat / fading | 0.039% / 0.039% / 0.033% | Position building in range | 84.2% | 0.0% | 15.8% | 2.74x | 0.020% / 0.072% |
| 2026-05-02 14:00 | 2.77x | Doji / lower rejection | Flat / fading | -0.026% / 0.007% / 0.007% | Weak move without breakout | 0.0% | 27.3% | 72.7% | 1.59x | 0.039% / 0.039% |
| 2026-05-02 18:30 | 2.76x | Small-body bearish | Impulse / continuation | 0.013% / 0.013% / 0.013% | True breakout | 50.0% | 16.7% | 33.3% | 1.38x | 0.046% / 0.046% |
| 2026-05-02 18:45 | 2.74x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / 0.007% / 0.013% | Weak move without breakout | 18.2% | 0.0% | 81.8% | 2.41x | 0.046% / 0.033% |
| 2026-05-03 12:15 | 8.33x | Full-bodied bullish | Impulse / continuation | 0.111% / 0.059% / 0.065% | True breakout | 66.7% | 20.0% | 13.3% | 3.09x | 0.170% / 0.059% |
| 2026-05-03 12:30 | 6.70x | Small-body bullish | Flat / fading | -0.052% / -0.078% / -0.072% | Position building in range | 48.6% | 25.7% | 25.7% | 6.20x | -0.007% / 0.098% |
| 2026-05-04 07:00 | 39.02x | Full-bodied bullish | Impulse / continuation | 0.091% / 0.098% / 0.287% | True breakout | 73.9% | 26.1% | 0.0% | 17.56x | 0.332% / 0.007% |
| 2026-05-04 07:15 | 6.72x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.007% / 0.228% / 0.007% | True breakout | 33.3% | 64.3% | 2.4% | 4.82x | 0.241% / 0.039% |
| 2026-05-04 07:30 | 4.91x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.221% / 0.189% / 0.078% | True breakout | 3.3% | 76.7% | 20.0% | 2.59x | 0.234% / 0.091% |
| 2026-05-04 07:45 | 3.00x | Full-bodied bullish | Flat / fading | -0.032% / -0.221% / -0.208% | Weak move without breakout | 85.0% | 0.0% | 15.0% | 2.98x | 0.013% / 0.312% |
| 2026-05-04 08:00 | 2.77x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.188% / -0.110% / 0.078% | False breakout | 20.0% | 15.0% | 65.0% | 1.26x | 0.279% / 0.123% |
| 2026-05-04 08:15 | 2.66x | Full-bodied bearish | Reversal | 0.078% / 0.013% / 0.221% | Liquidity sweep / reversal | 90.6% | 6.3% | 3.1% | 1.87x | 0.091% / 0.312% |
| 2026-05-04 09:00 | 7.42x | Full-bodied bullish | Flat / fading | -0.045% / -0.110% / 0.058% | Weak move without breakout | 84.8% | 15.2% | 0.0% | 2.14x | 0.084% / 0.331% |
| 2026-05-04 11:15 | 2.09x | Full-bodied bearish | Impulse / continuation | -0.104% / -0.235% / -0.378% | True breakout | 93.6% | 0.0% | 6.4% | 1.54x | 0.378% / 0.007% |
| 2026-05-04 11:30 | 2.60x | Bullish pin-bar / lower rejection | Flat / fading | -0.130% / -0.013% / -0.189% | Weak move without breakout | 27.5% | 5.9% | 66.7% | 1.65x | 0.280% / 0.046% |
| 2026-05-04 14:00 | 5.36x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.177% / -0.315% / -0.362% | True breakout | 53.9% | 0.0% | 46.1% | 3.52x | 0.716% / 0.046% |
| 2026-05-04 14:45 | 2.49x | Full-bodied bearish | Reversal | 0.225% / 0.397% / 0.615% | Liquidity sweep / reversal | 67.2% | 0.0% | 32.8% | 1.36x | 0.053% / 0.688% |
| 2026-05-05 11:00 | 4.34x | Small-body bearish | Impulse -> reversal | -0.297% / -0.053% / 0.475% | False breakout | 59.3% | 25.4% | 15.3% | 2.12x | 0.357% / 0.535% |
| 2026-05-05 11:15 | 5.34x | Full-bodied bearish | Reversal | 0.245% / 0.344% / 1.000% | Liquidity sweep / reversal | 77.8% | 5.6% | 16.7% | 1.77x | 0.046% / 1.066% |
| 2026-05-05 12:00 | 2.55x | Full-bodied bullish | Impulse / continuation | 0.223% / 0.618% / 0.467% | True breakout | 81.2% | 11.3% | 7.5% | 2.18x | 0.933% / 0.000% |
| 2026-05-05 12:15 | 3.63x | Full-bodied bullish | Impulse / continuation | 0.393% / 0.544% / 0.308% | True breakout | 75.0% | 22.7% | 2.3% | 1.05x | 0.708% / 0.046% |
| 2026-05-05 12:30 | 6.12x | Full-bodied bullish | Flat / fading | 0.150% / -0.150% / 0.340% | Weak move without breakout | 68.1% | 26.4% | 5.5% | 2.04x | 0.346% / 0.209% |
| 2026-05-05 13:00 | 2.65x | Full-bodied bearish | Reversal | 0.065% / 0.491% / 0.314% | Liquidity sweep / reversal | 67.2% | 26.9% | 6.0% | 1.37x | 0.059% / 0.700% |
| 2026-05-05 16:45 | 3.65x | Full-bodied bullish | Impulse / continuation | -0.142% / 0.162% / 0.181% | True breakout | 87.1% | 12.9% | 0.0% | 2.14x | 0.472% / 0.174% |
| 2026-05-06 07:00 | 2.52x | Bullish pin-bar / lower rejection | Flat / fading | -0.006% / -0.026% / -0.006% | Weak move without breakout | 20.3% | 12.5% | 67.2% | 3.69x | 0.090% / 0.077% |
| 2026-05-06 09:00 | 4.67x | Full-bodied bearish | Impulse / continuation | -0.311% / -0.252% / -0.356% | True breakout | 72.6% | 3.2% | 24.2% | 2.90x | 0.595% / 0.006% |
| 2026-05-06 09:15 | 5.26x | Full-bodied bearish | Flat / fading | 0.058% / -0.045% / -0.110% | Weak move without breakout | 62.3% | 1.3% | 36.4% | 3.05x | 0.286% / 0.227% |
| 2026-05-06 09:30 | 2.62x | Bearish pin-bar / upper rejection | Reversal | -0.104% / -0.104% / -0.337% | Liquidity sweep / reversal | 25.0% | 65.0% | 10.0% | 1.34x | 0.162% / 0.415% |
| 2026-05-06 10:00 | 3.60x | Bearish pin-bar / upper rejection | Reversal | -0.065% / -0.234% / 0.175% | Liquidity sweep / reversal | 1.3% | 51.3% | 47.4% | 2.53x | 0.312% / 0.214% |
| 2026-05-06 10:30 | 3.00x | Small-body bearish | Reversal | 0.117% / 0.410% / 1.081% | Liquidity sweep / reversal | 43.9% | 35.1% | 21.1% | 1.57x | 0.007% / 1.224% |
| 2026-05-06 11:15 | 2.95x | Full-bodied bullish | Impulse / continuation | 0.226% / 0.071% / -0.342% | True breakout | 77.1% | 2.4% | 20.5% | 2.09x | 0.368% / 0.432% |
| 2026-05-06 11:30 | 2.71x | Small-body bullish | Reversal | -0.155% / -0.232% / -0.560% | Liquidity sweep / reversal | 55.6% | 34.9% | 9.5% | 1.42x | 0.077% / 0.760% |
| 2026-05-06 13:00 | 2.79x | Bullish pin-bar / lower rejection | Reversal | 0.091% / -0.046% / 0.150% | Liquidity sweep / reversal | 16.7% | 18.9% | 64.4% | 1.68x | 0.260% / 0.260% |
| 2026-05-06 17:45 | 4.78x | Full-bodied bullish | Flat / fading | -0.039% / -0.064% / -0.103% | Position building in range | 83.0% | 17.0% | 0.0% | 3.23x | 0.110% / 0.110% |
| 2026-05-06 19:00 | 2.51x | Bearish pin-bar / upper rejection | Reversal | -0.245% / -0.432% / -0.400% | Liquidity sweep / reversal | 9.4% | 62.5% | 28.1% | 2.06x | -0.006% / 0.677% |
| 2026-05-07 09:00 | 4.52x | Bullish pin-bar / lower rejection | Flat / fading | -0.006% / -0.148% / -0.219% | Weak move without breakout | 56.7% | 3.0% | 40.3% | 3.47x | 0.110% / 0.277% |
| 2026-05-07 09:15 | 3.82x | Bullish pin-bar / lower rejection | Reversal | -0.142% / 0.013% / -0.103% | Liquidity sweep / reversal | 3.3% | 40.0% | 56.7% | 1.29x | 0.381% / 0.116% |
| 2026-05-07 09:30 | 2.54x | Bearish pin-bar / upper rejection | Reversal | 0.155% / -0.071% / -0.013% | Liquidity sweep / reversal | 53.7% | 43.9% | 2.4% | 1.73x | 0.239% / 0.162% |
| 2026-05-07 10:15 | 3.27x | Bullish pin-bar / lower rejection | Reversal | -0.052% / -0.065% / -0.187% | Liquidity sweep / reversal | 32.1% | 18.9% | 49.1% | 1.91x | 0.194% / 0.213% |
| 2026-05-07 12:30 | 4.08x | Full-bodied bullish | Impulse / continuation | 0.155% / 0.123% / 0.065% | True breakout | 75.6% | 19.5% | 4.9% | 1.26x | 0.374% / 0.071% |
| 2026-05-07 13:00 | 4.51x | Bearish pin-bar / upper rejection | Flat / fading | -0.084% / -0.058% / -0.077% | Weak move without breakout | 10.0% | 87.5% | 2.5% | 1.29x | 0.193% / 0.013% |
| 2026-05-07 16:30 | 2.66x | Full-bodied bearish | Flat / fading | 0.130% / 0.032% / 0.065% | Position building in range | 61.1% | 0.0% | 38.9% | 1.73x | 0.026% / 0.188% |
| 2026-05-07 18:15 | 2.96x | Full-bodied bearish | Flat / fading | 0.019% / 0.078% / 0.110% | Position building in range | 60.9% | 4.3% | 34.8% | 1.56x | 0.019% / 0.169% |
| 2026-05-08 09:00 | 3.20x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.130% / -0.091% / -0.052% | True breakout | 8.0% | 60.0% | 32.0% | 2.54x | 0.260% / 0.006% |
| 2026-05-08 09:15 | 5.50x | Bullish pin-bar / lower rejection | Reversal | 0.039% / 0.026% / 0.221% | Liquidity sweep / reversal | 51.2% | 0.0% | 48.8% | 3.78x | 0.065% / 0.279% |
| 2026-05-08 11:00 | 2.53x | Bearish pin-bar / upper rejection | Reversal | -0.110% / -0.181% / -0.194% | Liquidity sweep / reversal | 43.3% | 56.7% | 0.0% | 1.74x | 0.045% / 0.253% |
| 2026-05-08 12:15 | 2.68x | Small-body bearish | Impulse / continuation | 0.013% / 0.033% / -0.397% | True breakout | 57.1% | 2.9% | 40.0% | 1.55x | 0.423% / 0.111% |
| 2026-05-08 13:15 | 3.93x | Full-bodied bearish | Flat / fading | 0.124% / 0.144% / 0.111% | Weak move without breakout | 91.2% | 1.8% | 7.0% | 2.53x | 0.059% / 0.255% |
| 2026-05-08 13:45 | 2.09x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.033% / -0.059% | Liquidity sweep / reversal | 15.0% | 85.0% | 0.0% | 0.77x | 0.111% / 0.130% |
| 2026-05-08 15:45 | 2.20x | Full-bodied bearish | Impulse / continuation | -0.079% / -0.137% / -0.242% | True breakout | 89.5% | 5.3% | 5.3% | 1.67x | 0.425% / 0.033% |
| 2026-05-08 16:30 | 2.25x | Full-bodied bearish | Flat / fading | 0.158% / 0.131% / 0.105% | Position building in range | 83.3% | 9.3% | 7.4% | 2.28x | 0.020% / 0.263% |
| 2026-05-08 21:00 | 6.25x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.267% / 0.117% / 0.599% | True breakout | 48.1% | 45.3% | 6.6% | 5.03x | 0.670% / 0.280% |
| 2026-05-08 21:15 | 2.70x | Small-body bullish | Impulse / continuation | -0.149% / 0.234% / 0.324% | True breakout | 46.9% | 14.3% | 38.8% | 3.59x | 0.402% / 0.279% |
| 2026-05-08 21:45 | 2.53x | Full-bodied bullish | Flat / fading | 0.097% / 0.091% / -0.006% | Weak move without breakout | 96.8% | 0.0% | 3.2% | 1.80x | 0.168% / 0.129% |
| 2026-05-11 12:30 | 2.97x | Full-bodied bullish | Reversal | -0.019% / -0.314% / -0.295% | Liquidity sweep / reversal | 85.7% | 14.3% | 0.0% | 2.23x | 0.051% / 0.333% |
| 2026-05-11 13:00 | 2.77x | Full-bodied bearish | Flat / fading | 0.071% / 0.019% / 0.019% | Position building in range | 82.1% | 12.5% | 5.4% | 2.30x | 0.013% / 0.103% |
| 2026-05-11 16:00 | 2.95x | Bullish pin-bar / lower rejection | Flat / fading | -0.103% / -0.090% / -0.006% | Position building in range | 58.7% | 0.0% | 41.3% | 2.29x | 0.110% / 0.026% |
| 2026-05-11 19:45 | 4.58x | Bullish pin-bar / lower rejection | Reversal | 0.013% / 0.039% / 0.174% | Liquidity sweep / reversal | 31.9% | 6.4% | 61.7% | 3.60x | 0.129% / 0.193% |
| 2026-05-11 20:30 | 3.13x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.084% / 0.122% / 0.206% | True breakout | 30.4% | 17.4% | 52.2% | 1.42x | 0.258% / 0.032% |
| 2026-05-12 07:00 | 4.34x | Bearish pin-bar / upper rejection | Reversal | -0.064% / 0.006% / -0.013% | Liquidity sweep / reversal | 13.3% | 46.7% | 40.0% | 1.85x | 0.071% / 0.141% |
| 2026-05-12 09:00 | 4.05x | Bullish pin-bar / lower rejection | Reversal | -0.058% / -0.058% / 0.225% | Liquidity sweep / reversal | 32.4% | 17.6% | 50.0% | 1.90x | 0.161% / 0.251% |
| 2026-05-12 10:00 | 2.58x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.173% / 0.423% | True breakout | 77.4% | 6.5% | 16.1% | 3.19x | 0.629% / 0.096% |
| 2026-05-12 10:30 | 7.66x | Full-bodied bullish | Impulse / continuation | 0.224% / 0.250% / 0.199% | True breakout | 76.3% | 18.4% | 5.3% | 1.63x | 0.455% / 0.000% |
| 2026-05-12 10:45 | 3.92x | Full-bodied bullish | Flat / fading | 0.026% / -0.006% / -0.045% | Weak move without breakout | 70.0% | 30.0% | 0.0% | 2.10x | 0.230% / 0.128% |
| 2026-05-13 07:00 | 2.63x | Full-bodied bearish | Flat / fading | 0.044% / 0.063% / 0.044% | Weak move without breakout | 82.1% | 1.5% | 16.4% | 3.22x | 0.076% / 0.177% |
| 2026-05-13 17:45 | 4.68x | Full-bodied bullish | Flat / fading | -0.076% / -0.025% / -0.044% | Position building in range | 69.7% | 15.2% | 15.2% | 2.05x | 0.013% / 0.120% |
| 2026-05-13 20:15 | 6.14x | Full-bodied bullish | Impulse / continuation | 0.025% / -0.025% / 0.195% | True breakout | 94.3% | 4.3% | 1.4% | 4.21x | 0.421% / 0.082% |
| 2026-05-13 21:00 | 4.18x | Full-bodied bullish | Flat / fading | -0.119% / -0.263% / -0.282% | Weak move without breakout | 90.0% | 5.0% | 5.0% | 2.94x | 0.107% / 0.382% |
| 2026-05-14 09:30 | 2.64x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.088% / -0.151% / 0.019% | True breakout | 54.8% | 0.0% | 45.2% | 1.56x | 0.214% / 0.057% |
| 2026-05-14 09:45 | 2.53x | Bullish pin-bar / lower rejection | Reversal | -0.063% / 0.063% / -0.315% | Liquidity sweep / reversal | 35.9% | 12.8% | 51.3% | 1.81x | 0.365% / 0.151% |
| 2026-05-14 10:00 | 3.56x | Bearish pin-bar / upper rejection | Reversal | 0.126% / 0.170% / -0.094% | Liquidity sweep / reversal | 27.9% | 48.8% | 23.3% | 1.90x | 0.302% / 0.214% |
| 2026-05-14 10:45 | 7.03x | Full-bodied bearish | Impulse / continuation | 0.158% / 0.057% / -0.152% | True breakout | 80.5% | 9.8% | 9.8% | 3.38x | 0.328% / 0.189% |
| 2026-05-14 18:30 | 2.87x | Bullish pin-bar / lower rejection | Flat / fading | -0.019% / -0.089% / -0.057% | Weak move without breakout | 54.1% | 0.0% | 45.9% | 1.80x | 0.191% / 0.013% |
| 2026-05-15 07:00 | 6.55x | Bullish pin-bar / lower rejection | Flat / fading | 0.051% / 0.032% / 0.083% | Weak move without breakout | 39.1% | 0.0% | 60.9% | 5.03x | 0.045% / 0.210% |
| 2026-05-15 10:00 | 6.37x | Full-bodied bullish | Reversal | -0.025% / -0.076% / -0.304% | Liquidity sweep / reversal | 61.5% | 36.9% | 1.5% | 2.44x | 0.127% / 0.355% |
| 2026-05-15 11:30 | 2.58x | Bullish pin-bar / lower rejection | Reversal | 0.076% / 0.261% / 0.134% | Liquidity sweep / reversal | 50.0% | 3.8% | 46.2% | 1.79x | 0.006% / 0.267% |
| 2026-05-15 17:00 | 4.60x | Full-bodied bearish | Impulse / continuation | -0.006% / -0.160% / -0.546% | True breakout | 84.9% | 4.1% | 11.0% | 3.28x | 0.648% / 0.077% |
| 2026-05-15 17:30 | 4.28x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.373% / -0.386% / -0.624% | True breakout | 42.6% | 0.0% | 57.4% | 2.04x | 0.791% / 0.013% |
| 2026-05-15 17:45 | 3.99x | Full-bodied bearish | Impulse / continuation | -0.013% / -0.058% / 0.026% | True breakout | 92.3% | 0.0% | 7.7% | 2.21x | 0.419% / 0.032% |
| 2026-05-15 18:30 | 4.55x | Bullish pin-bar / lower rejection | Reversal | 0.278% / 0.239% / -0.052% | Liquidity sweep / reversal | 46.0% | 12.7% | 41.3% | 1.87x | 0.136% / 0.285% |
| 2026-05-16 10:45 | 2.52x | Full-bodied bullish | Flat / fading | -0.084% / -0.019% / -0.039% | Position building in range | 81.6% | 10.5% | 7.9% | 3.80x | 0.013% / 0.103% |
| 2026-05-16 11:00 | 2.80x | Full-bodied bearish | Flat / fading | 0.065% / 0.065% / 0.052% | Position building in range | 72.2% | 11.1% | 16.7% | 1.55x | 0.019% / 0.090% |
| 2026-05-16 17:30 | 3.53x | Small-body bullish | Reversal | -0.065% / -0.078% / -0.149% | Liquidity sweep / reversal | 50.0% | 33.3% | 16.7% | 4.80x | 0.026% / 0.155% |
| 2026-05-16 17:45 | 6.83x | Small-body bearish | Impulse / continuation | -0.013% / -0.045% / -0.097% | True breakout | 52.6% | 21.1% | 26.3% | 6.19x | 0.116% / 0.013% |
| 2026-05-16 18:30 | 3.59x | Full-bodied bearish | Reversal | -0.013% / 0.110% / 0.226% | Liquidity sweep / reversal | 90.0% | 0.0% | 10.0% | 2.09x | 0.032% / 0.246% |
| 2026-05-17 10:15 | 3.48x | Full-bodied bullish | Flat / fading | -0.052% / -0.052% / -0.045% | Position building in range | 68.0% | 12.0% | 20.0% | 3.07x | 0.000% / 0.077% |
| 2026-05-18 07:00 | 28.40x | Bearish pin-bar / upper rejection | Reversal | 0.052% / -0.187% / -0.187% | Liquidity sweep / reversal | 44.4% | 52.8% | 2.8% | 5.36x | 0.129% / 0.271% |
| 2026-05-18 07:15 | 5.87x | Small-body bullish | Reversal | -0.239% / -0.135% / -0.290% | Liquidity sweep / reversal | 25.0% | 37.5% | 37.5% | 3.58x | -0.019% / 0.387% |
| 2026-05-18 07:30 | 5.75x | Full-bodied bearish | Flat / fading | 0.103% / 0.000% / -0.078% | Weak move without breakout | 68.1% | 4.3% | 27.7% | 4.42x | 0.149% / 0.103% |
| 2026-05-18 09:00 | 10.46x | Full-bodied bearish | Impulse / continuation | 0.032% / 0.039% / -0.136% | True breakout | 67.6% | 9.9% | 22.5% | 3.82x | 0.312% / 0.123% |
| 2026-05-18 10:00 | 3.33x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.299% / -0.442% / -0.247% | True breakout | 40.0% | 6.0% | 54.0% | 1.92x | 0.612% / -0.007% |
| 2026-05-18 10:15 | 4.12x | Full-bodied bearish | Flat / fading | -0.144% / -0.026% / 0.196% | Weak move without breakout | 66.2% | 0.0% | 33.8% | 2.33x | 0.313% / 0.228% |
| 2026-05-18 10:30 | 3.99x | Bullish pin-bar / lower rejection | Reversal | 0.118% / 0.196% / 0.294% | Liquidity sweep / reversal | 37.3% | 18.6% | 44.1% | 1.74x | 0.144% / 0.386% |
| 2026-05-18 10:45 | 2.67x | Bearish pin-bar / upper rejection | Flat / fading | 0.078% / 0.222% / 0.046% | Weak move without breakout | 28.4% | 40.3% | 31.3% | 1.89x | 0.268% / 0.026% |
| 2026-05-18 17:15 | 2.94x | Full-bodied bullish | Impulse / continuation | 0.085% / 0.475% / 0.690% | True breakout | 70.0% | 30.0% | 0.0% | 1.85x | 0.742% / 0.059% |
| 2026-05-18 17:45 | 3.98x | Full-bodied bullish | Impulse / continuation | 0.149% / 0.214% / 0.486% | True breakout | 98.4% | 0.0% | 1.6% | 2.77x | 0.550% / 0.006% |
| 2026-05-18 18:30 | 5.25x | Full-bodied bullish | Impulse / continuation | -0.006% / 0.232% / 0.168% | True breakout | 79.6% | 16.7% | 3.7% | 2.21x | 0.283% / 0.103% |
| 2026-05-18 19:00 | 2.69x | Full-bodied bullish | Impulse / continuation | -0.045% / -0.064% / 0.148% | True breakout | 85.7% | 4.8% | 9.5% | 1.54x | 0.264% / 0.116% |
| 2026-05-19 07:00 | 2.60x | Bearish pin-bar / upper rejection | Flat / fading | 0.148% / 0.148% / 0.148% | Position building in range | 52.7% | 43.6% | 3.6% | 4.30x | 0.006% / 0.212% |
| 2026-05-19 09:15 | 2.72x | Small-body bearish | Flat / fading | 0.000% / 0.006% / -0.128% | Weak move without breakout | 40.9% | 31.8% | 27.3% | 1.90x | 0.193% / 0.077% |
| 2026-05-19 11:00 | 12.21x | Full-bodied bullish | Impulse / continuation | -0.038% / 0.190% / 0.527% | True breakout | 86.2% | 13.2% | 0.6% | 6.60x | 0.597% / 0.102% |
| 2026-05-19 11:45 | 4.20x | Bearish pin-bar / upper rejection | Reversal | 0.253% / -0.057% / -0.266% | Liquidity sweep / reversal | 18.3% | 65.0% | 16.7% | 1.44x | 0.323% / 0.272% |
| 2026-05-19 12:00 | 2.84x | Full-bodied bullish | Reversal | -0.309% / -0.297% / -1.086% | Liquidity sweep / reversal | 76.5% | 21.6% | 2.0% | 1.20x | 0.006% / 1.117% |
| 2026-05-20 08:00 | 5.73x | Bearish pin-bar / upper rejection | Reversal | -0.006% / -0.063% / -0.317% | Liquidity sweep / reversal | 32.7% | 67.3% | 0.0% | 3.74x | 0.013% / 0.374% |
| 2026-05-20 09:00 | 3.34x | Full-bodied bearish | Impulse / continuation | 0.134% / -0.121% / -0.223% | True breakout | 82.5% | 1.8% | 15.8% | 3.03x | 0.401% / 0.172% |
| 2026-05-20 09:15 | 2.86x | Full-bodied bullish | Reversal | -0.254% / -0.273% / -0.426% | Liquidity sweep / reversal | 61.4% | 0.0% | 38.6% | 1.97x | 0.038% / 0.534% |
| 2026-05-20 09:45 | 3.23x | Bullish pin-bar / lower rejection | Flat / fading | -0.083% / -0.153% / -0.166% | Weak move without breakout | 10.0% | 40.0% | 50.0% | 1.83x | 0.261% / 0.038% |
| 2026-05-20 10:00 | 4.08x | Bullish pin-bar / lower rejection | Flat / fading | -0.070% / -0.051% / -0.115% | Position building in range | 38.3% | 2.1% | 59.6% | 1.59x | 0.172% / 0.070% |
| 2026-05-20 11:15 | 4.13x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.096% / -0.064% / -0.390% | True breakout | 33.3% | 3.7% | 63.0% | 0.81x | 0.575% / 0.000% |
| 2026-05-20 12:15 | 2.30x | Bullish pin-bar / lower rejection | Reversal | 0.160% / 0.295% / 0.423% | Liquidity sweep / reversal | 37.1% | 16.1% | 46.8% | 1.85x | 0.000% / 0.481% |
| 2026-05-20 17:45 | 3.65x | Full-bodied bullish | Flat / fading | 0.013% / -0.077% / 0.013% | Weak move without breakout | 62.9% | 9.7% | 27.4% | 2.31x | 0.070% / 0.160% |
| 2026-05-20 20:30 | 4.07x | Bullish pin-bar / lower rejection | Flat / fading | -0.019% / -0.026% / -0.032% | Position building in range | 28.7% | 7.4% | 63.8% | 3.66x | 0.102% / 0.013% |
| 2026-05-21 09:15 | 4.97x | Bullish pin-bar / lower rejection | Reversal | -0.077% / -0.128% / -0.876% | Liquidity sweep / reversal | 34.7% | 0.0% | 65.3% | 2.78x | 0.147% / 1.029% |
| 2026-05-21 10:00 | 21.75x | Small-body bearish | Flat / fading | -0.129% / -0.039% / -0.200% | Weak move without breakout | 56.2% | 26.6% | 17.2% | 8.51x | 0.283% / 0.058% |
| 2026-05-21 10:15 | 4.08x | Bullish pin-bar / lower rejection | Flat / fading | 0.090% / -0.045% / 0.097% | Weak move without breakout | 44.2% | 0.0% | 55.8% | 1.39x | 0.123% / 0.187% |
| 2026-05-21 17:15 | 2.83x | Full-bodied bullish | Impulse / continuation | -0.051% / 0.173% / 0.173% | True breakout | 63.4% | 16.9% | 19.7% | 2.75x | 0.282% / 0.243% |
| 2026-05-21 17:30 | 3.34x | Bullish pin-bar / lower rejection | Reversal | 0.224% / 0.218% / 0.250% | Liquidity sweep / reversal | 7.9% | 44.4% | 47.6% | 2.12x | 0.032% / 0.359% |
| 2026-05-21 17:45 | 3.13x | Full-bodied bullish | Flat / fading | -0.006% / 0.000% / 0.070% | Weak move without breakout | 74.4% | 7.0% | 18.6% | 1.33x | 0.134% / 0.192% |
| 2026-05-22 09:45 | 5.71x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.217% / 0.415% / 0.332% | True breakout | 52.1% | 47.9% | 0.0% | 2.69x | 0.703% / 0.089% |
| 2026-05-22 10:00 | 3.17x | Full-bodied bullish | Impulse / continuation | 0.198% / 0.153% / -0.089% | True breakout | 69.4% | 2.0% | 28.6% | 2.55x | 0.484% / 0.198% |
| 2026-05-22 10:15 | 7.50x | Full-bodied bullish | Impulse -> reversal | -0.045% / -0.083% / -0.115% | False breakout | 69.8% | 27.9% | 2.3% | 2.01x | 0.286% / 0.394% |
| 2026-05-22 10:30 | 6.75x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.038% / -0.242% / -0.235% | True breakout | 13.5% | 86.5% | 0.0% | 2.12x | 0.350% / 0.083% |
| 2026-05-22 11:00 | 4.10x | Small-body bearish | Flat / fading | 0.172% / 0.006% / 0.019% | Weak move without breakout | 49.2% | 24.6% | 26.2% | 2.52x | 0.140% / 0.325% |
| 2026-05-22 11:15 | 4.29x | Bearish pin-bar / upper rejection | Reversal | -0.166% / -0.312% / -0.140% | Liquidity sweep / reversal | 46.2% | 46.2% | 7.7% | 1.74x | 0.083% / 0.312% |
| 2026-05-22 17:45 | 3.16x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.006% / -0.084% / -0.135% | True breakout | 24.0% | 62.0% | 14.0% | 1.41x | 0.599% / 0.116% |
| 2026-05-22 18:30 | 3.22x | Bullish pin-bar / lower rejection | Flat / fading | 0.058% / -0.071% / 0.045% | Position building in range | 20.5% | 3.6% | 75.9% | 2.29x | 0.116% / 0.077% |
| 2026-05-22 23:30 | 2.67x | Bullish pin-bar / lower rejection | Reversal | -0.052% / -1.400% / -1.142% | Liquidity sweep / reversal | 20.0% | 16.0% | 64.0% | 1.76x | 0.013% / 1.445% |
| 2026-05-23 16:00 | 3.90x | Bullish pin-bar / lower rejection | Reversal | 0.020% / 0.065% / 0.000% | Liquidity sweep / reversal | 57.1% | 0.0% | 42.9% | 1.46x | 0.026% / 0.072% |
| 2026-05-23 17:30 | 3.45x | Bullish pin-bar / lower rejection | Reversal | 0.039% / -0.007% / -0.013% | Liquidity sweep / reversal | 31.3% | 0.0% | 68.7% | 1.87x | 0.078% / 0.039% |
| 2026-05-24 16:45 | 4.23x | Small-body bullish | Flat / fading | 0.039% / 0.000% / 0.013% | Weak move without breakout | 54.5% | 27.3% | 18.2% | 2.70x | 0.039% / 0.052% |
| 2026-05-24 17:15 | 3.01x | Bullish pin-bar / lower rejection | Flat / fading | -0.013% / 0.013% / 0.000% | Weak move without breakout | 54.5% | 0.0% | 45.5% | 2.44x | 0.052% / 0.033% |
| 2026-05-24 18:45 | 2.62x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.000% / 0.124% / 0.091% | True breakout | 26.9% | 50.0% | 23.1% | 3.71x | 0.340% / 0.020% |
| 2026-05-25 07:00 | 14.15x | Bearish pin-bar / upper rejection | Flat / fading | 0.013% / -0.033% / 0.033% | Position building in range | 36.4% | 60.0% | 3.6% | 6.53x | 0.065% / 0.117% |
| 2026-05-25 07:15 | 4.13x | Bullish pin-bar / lower rejection | Reversal | -0.046% / -0.033% / 0.085% | Liquidity sweep / reversal | 14.3% | 38.1% | 47.6% | 1.75x | 0.111% / 0.130% |
| 2026-05-25 08:15 | 3.91x | Small-body bullish | Reversal | 0.007% / -0.059% / -0.026% | Liquidity sweep / reversal | 58.8% | 23.5% | 17.6% | 1.04x | 0.046% / 0.345% |
| 2026-05-25 08:30 | 2.81x | Bearish pin-bar / upper rejection | Reversal | -0.065% / -0.078% / -0.072% | Liquidity sweep / reversal | 10.0% | 60.0% | 30.0% | 0.60x | 0.072% / 0.352% |
| 2026-05-25 09:00 | 9.23x | Bullish pin-bar / lower rejection | Reversal | 0.046% / 0.007% / -0.026% | Liquidity sweep / reversal | 8.7% | 0.0% | 91.3% | 2.72x | 0.039% / 0.150% |
| 2026-05-25 09:15 | 4.35x | Bearish pin-bar / upper rejection | Reversal | -0.039% / 0.007% / 0.059% | Liquidity sweep / reversal | 46.7% | 40.0% | 13.3% | 0.77x | 0.104% / 0.176% |
| 2026-05-25 10:00 | 2.61x | Full-bodied bearish | Reversal | 0.130% / 0.065% / 0.072% | Liquidity sweep / reversal | 75.0% | 12.5% | 12.5% | 0.74x | 0.104% / 0.150% |
| 2026-05-25 10:15 | 3.00x | Bullish pin-bar / lower rejection | Flat / fading | -0.065% / -0.072% / 0.039% | Weak move without breakout | 51.4% | 2.7% | 45.9% | 1.77x | 0.046% / 0.235% |
| 2026-05-25 11:15 | 2.47x | Full-bodied bullish | Impulse / continuation | -0.007% / 0.098% / 0.332% | True breakout | 78.9% | 5.3% | 15.8% | 0.89x | 0.430% / 0.091% |
| 2026-05-25 11:45 | 2.21x | Small-body bullish | Impulse / continuation | 0.299% / 0.234% / 0.078% | True breakout | 54.8% | 16.1% | 29.0% | 1.50x | 0.332% / 0.065% |
| 2026-05-25 12:00 | 3.83x | Full-bodied bullish | Flat / fading | -0.065% / -0.104% / -0.240% | Position building in range | 73.8% | 8.2% | 18.0% | 2.81x | 0.000% / 0.272% |
| 2026-05-25 16:30 | 6.00x | Full-bodied bearish | Impulse / continuation | -0.223% / -0.288% / -0.426% | True breakout | 74.8% | 2.7% | 22.5% | 3.70x | 0.852% / 0.007% |
| 2026-05-25 16:45 | 4.02x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.066% / -0.427% / -0.118% | True breakout | 50.7% | 1.5% | 47.8% | 1.92x | 0.631% / 0.026% |
| 2026-05-25 17:15 | 3.67x | Full-bodied bearish | Flat / fading | 0.224% / 0.310% / 0.211% | Weak move without breakout | 65.6% | 0.0% | 34.4% | 2.47x | 0.132% / 0.402% |
| 2026-05-26 11:00 | 3.45x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.224% / 0.046% / 0.092% | False breakout | 27.9% | 16.3% | 55.8% | 1.61x | 0.469% / 0.125% |
| 2026-05-26 11:15 | 5.43x | Bullish pin-bar / lower rejection | Reversal | 0.271% / 0.139% / 0.463% | Liquidity sweep / reversal | 49.3% | 0.0% | 50.7% | 2.55x | 0.013% / 0.523% |
| 2026-05-26 17:15 | 2.67x | Full-bodied bullish | Flat / fading | -0.218% / -0.185% / -0.172% | Position building in range | 66.7% | 3.9% | 29.4% | 2.08x | 0.007% / 0.290% |
| 2026-05-26 19:00 | 5.81x | Full-bodied bearish | Impulse / continuation | 0.027% / -0.113% / -0.066% | True breakout | 77.6% | 6.9% | 15.5% | 2.43x | 0.358% / 0.060% |
| 2026-05-26 19:15 | 3.57x | Bullish pin-bar / lower rejection | Reversal | -0.139% / -0.258% / 0.159% | Liquidity sweep / reversal | 15.0% | 12.5% | 72.5% | 1.54x | 0.205% / 0.384% |
| 2026-05-26 19:45 | 3.99x | Bullish pin-bar / lower rejection | Reversal | 0.166% / 0.419% / 0.744% | Liquidity sweep / reversal | 48.6% | 0.0% | 51.4% | 1.34x | 0.020% / 0.831% |
| 2026-05-26 20:15 | 3.04x | Full-bodied bullish | Impulse / continuation | 0.079% / 0.324% / 0.278% | True breakout | 62.3% | 11.5% | 26.2% | 2.05x | 0.509% / 0.152% |
| 2026-05-26 20:30 | 2.74x | Bearish pin-bar / upper rejection | Flat / fading | 0.245% / 0.205% / 0.165% | Weak move without breakout | 17.5% | 56.2% | 26.3% | 2.42x | 0.430% / 0.013% |
| 2026-05-26 21:00 | 2.58x | Bearish pin-bar / upper rejection | Flat / fading | -0.007% / -0.040% / -0.099% | Weak move without breakout | 12.0% | 56.0% | 32.0% | 1.31x | 0.172% / 0.099% |
| 2026-05-27 10:00 | 3.22x | Small-body bullish | Reversal | -0.257% / -0.501% / -0.586% | Liquidity sweep / reversal | 49.1% | 29.1% | 21.8% | 1.49x | 0.053% / 0.758% |
| 2026-05-27 11:00 | 2.75x | Bullish pin-bar / lower rejection | Reversal | -0.166% / -0.033% / 0.133% | Liquidity sweep / reversal | 26.2% | 11.9% | 61.9% | 1.18x | 0.172% / 0.557% |
| 2026-05-27 11:45 | 3.93x | Small-body bullish | Flat / fading | -0.211% / -0.145% / -0.040% | Position building in range | 59.8% | 34.8% | 5.4% | 2.50x | 0.099% / 0.244% |
| 2026-05-28 07:00 | 4.22x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.000% / 0.033% / 0.000% | True breakout | 52.2% | 4.3% | 43.5% | 5.11x | 0.092% / 0.085% |
| 2026-05-28 11:00 | 2.93x | Full-bodied bullish | Impulse / continuation | 0.210% / 0.256% / 0.125% | True breakout | 82.2% | 13.3% | 4.4% | 2.68x | 0.362% / 0.013% |
| 2026-05-28 11:15 | 5.64x | Full-bodied bullish | Flat / fading | 0.046% / -0.079% / -0.105% | Weak move without breakout | 67.3% | 32.7% | 0.0% | 2.62x | 0.151% / 0.223% |
| 2026-05-28 11:30 | 2.81x | Bearish pin-bar / upper rejection | Reversal | -0.125% / -0.131% / -0.007% | Liquidity sweep / reversal | 27.3% | 54.5% | 18.2% | 1.07x | 0.105% / 0.269% |
| 2026-05-28 14:45 | 3.11x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.367% / -0.348% / -0.518% | True breakout | 57.9% | 0.0% | 42.1% | 1.67x | 0.531% / 0.046% |
| 2026-05-28 15:00 | 3.08x | Full-bodied bearish | Impulse / continuation | 0.020% / 0.086% / -0.474% | True breakout | 63.6% | 8.0% | 28.4% | 4.00x | 0.652% / 0.132% |
| 2026-05-28 16:00 | 4.39x | Full-bodied bearish | Flat / fading | 0.112% / 0.126% / 0.093% | Weak move without breakout | 64.0% | 0.0% | 36.0% | 2.84x | 0.238% / 0.132% |
| 2026-05-29 09:15 | 8.30x | Small-body bullish | Reversal | -0.112% / -0.244% / -0.356% | Liquidity sweep / reversal | 53.8% | 21.5% | 24.6% | 3.45x | 0.026% / 0.601% |
| 2026-05-29 10:15 | 5.84x | Bullish pin-bar / lower rejection | Flat / fading | -0.152% / -0.152% / -0.020% | Position building in range | 47.9% | 0.0% | 52.1% | 2.73x | 0.219% / 0.099% |
| 2026-05-29 14:30 | 3.03x | Bullish pin-bar / lower rejection | Reversal | 0.119% / 0.146% / -0.212% | Liquidity sweep / reversal | 29.6% | 25.9% | 44.4% | 1.07x | 0.179% / 0.338% |
| 2026-05-29 23:00 | 8.35x | Full-bodied bearish | Reversal | 0.000% / -0.027% / 0.060% | Liquidity sweep / reversal | 70.0% | 30.0% | 0.0% | 0.82x | 0.053% / 0.060% |
| 2026-05-30 15:15 | 2.86x | Full-bodied bullish | Reversal | -0.013% / -0.007% / -0.033% | Liquidity sweep / reversal | 66.7% | 16.7% | 16.7% | 1.45x | 0.000% / 0.040% |
| 2026-05-30 17:45 | 5.67x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / -0.013% / -0.013% | Weak move without breakout | 33.3% | 16.7% | 50.0% | 1.79x | 0.033% / 0.007% |
| 2026-05-31 10:00 | 3.15x | Bullish pin-bar / lower rejection | Reversal | -0.007% / -0.040% / -0.013% | Liquidity sweep / reversal | 50.0% | 0.0% | 50.0% | 1.79x | 0.000% / 0.046% |
| 2026-05-31 11:15 | 4.71x | Bullish pin-bar / lower rejection | Reversal | -0.020% / -0.020% / -0.013% | Liquidity sweep / reversal | 50.0% | 0.0% | 50.0% | 0.90x | 0.000% / 0.040% |
| 2026-05-31 18:30 | 5.43x | Doji / lower rejection | Impulse / continuation | 0.007% / 0.120% / 0.186% | True breakout | 0.0% | 10.0% | 90.0% | 2.30x | 0.246% / 0.246% |
| 2026-06-01 07:00 | 21.20x | Small-body bullish | Impulse / continuation | -0.020% / -0.040% / -0.040% | True breakout | 44.8% | 20.7% | 34.5% | 5.08x | 0.146% / 0.099% |
| 2026-06-01 07:15 | 5.29x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.020% / -0.007% / 0.086% | False breakout | 33.3% | 55.6% | 11.1% | 1.24x | 0.080% / 0.166% |
| 2026-06-01 07:30 | 13.87x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.013% / 0.000% / 0.053% | False breakout | 6.9% | 89.7% | 3.4% | 3.83x | 0.060% / 0.119% |
| 2026-06-01 08:15 | 3.09x | Full-bodied bullish | Impulse / continuation | -0.053% / -0.026% / 0.152% | True breakout | 72.7% | 9.1% | 18.2% | 2.15x | 0.192% / 0.093% |
| 2026-06-01 09:15 | 4.74x | Full-bodied bullish | Impulse / continuation | 0.159% / 0.106% / 0.264% | True breakout | 78.1% | 18.8% | 3.1% | 2.26x | 0.536% / 0.000% |
| 2026-06-01 09:30 | 4.41x | Full-bodied bullish | Impulse / continuation | -0.053% / 0.238% / 0.040% | True breakout | 66.7% | 33.3% | 0.0% | 2.20x | 0.376% / 0.125% |
| 2026-06-01 10:00 | 9.24x | Full-bodied bullish | Flat / fading | -0.132% / -0.198% / -0.158% | Position building in range | 65.6% | 32.8% | 1.6% | 3.32x | 0.066% / 0.250% |
| 2026-06-01 10:15 | 3.05x | Small-body bearish | Impulse / continuation | -0.066% / 0.026% / 0.033% | True breakout | 54.3% | 31.4% | 14.3% | 1.48x | 0.211% / 0.092% |
| 2026-06-01 19:30 | 6.90x | Small-body bullish | Flat / fading | 0.066% / 0.066% / -0.013% | Position building in range | 53.6% | 35.7% | 10.7% | 4.90x | 0.158% / 0.059% |
| 2026-06-02 09:00 | 4.97x | Bullish pin-bar / lower rejection | Reversal | 0.092% / 0.026% / 0.020% | Liquidity sweep / reversal | 34.6% | 3.8% | 61.5% | 2.00x | 0.066% / 0.145% |
| 2026-06-02 10:00 | 3.09x | Bullish pin-bar / lower rejection | Reversal | -0.033% / 0.316% / 0.639% | Liquidity sweep / reversal | 34.4% | 25.0% | 40.6% | 2.00x | 0.046% / 0.732% |
| 2026-06-02 10:30 | 6.52x | Full-bodied bullish | Impulse / continuation | 0.079% / 0.322% / 0.421% | True breakout | 72.6% | 27.4% | 0.0% | 4.06x | 0.513% / -0.020% |
| 2026-06-02 10:45 | 7.01x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.243% / 0.276% / 0.223% | True breakout | 20.0% | 80.0% | 0.0% | 2.23x | 0.433% / 0.046% |
| 2026-06-02 11:00 | 7.63x | Full-bodied bullish | Flat / fading | 0.033% / 0.098% / -0.059% | Weak move without breakout | 62.1% | 24.1% | 13.8% | 2.57x | 0.190% / 0.400% |
| 2026-06-02 11:30 | 3.49x | Bearish pin-bar / upper rejection | Reversal | -0.118% / -0.157% / 0.007% | Liquidity sweep / reversal | 37.5% | 58.3% | 4.2% | 0.92x | 0.105% / 0.497% |
| 2026-06-02 12:00 | 3.59x | Bullish pin-bar / lower rejection | Reversal | 0.092% / 0.164% / 0.203% | Liquidity sweep / reversal | 6.7% | 24.0% | 69.3% | 2.65x | 0.013% / 0.347% |
| 2026-06-02 17:30 | 3.36x | Bearish pin-bar / upper rejection | Flat / fading | 0.065% / 0.124% / 0.098% | Weak move without breakout | 28.9% | 71.1% | 0.0% | 1.54x | 0.215% / 0.059% |
| 2026-06-02 23:30 | 3.29x | Small-body bullish | Reversal | -0.019% / 0.026% / -0.104% | Liquidity sweep / reversal | 46.2% | 38.5% | 15.4% | 1.71x | 0.039% / 0.149% |
| 2026-06-03 07:45 | 3.37x | Bullish pin-bar / lower rejection | Flat / fading | -0.032% / -0.052% / -0.097% | Weak move without breakout | 2.9% | 38.2% | 58.8% | 2.26x | 0.156% / 0.006% |
| 2026-06-03 09:00 | 2.71x | Full-bodied bearish | Impulse / continuation | 0.085% / 0.026% / -0.169% | True breakout | 86.7% | 0.0% | 13.3% | 1.65x | 0.254% / 0.163% |
| 2026-06-03 10:00 | 2.92x | Full-bodied bearish | Impulse / continuation | -0.078% / -0.208% / -0.391% | True breakout | 77.2% | 0.0% | 22.8% | 2.90x | 0.397% / 0.059% |
| 2026-06-03 10:30 | 3.06x | Full-bodied bearish | Impulse / continuation | -0.085% / -0.183% / -0.157% | True breakout | 74.1% | 3.7% | 22.2% | 1.12x | 0.255% / 0.052% |
| 2026-06-03 15:30 | 4.05x | Full-bodied bearish | Flat / fading | -0.007% / 0.007% / -0.092% | Weak move without breakout | 77.6% | 2.6% | 19.7% | 4.24x | 0.111% / 0.085% |
| 2026-06-04 08:30 | 2.93x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.046% / 0.159% / 0.125% | True breakout | 21.4% | 50.0% | 28.6% | 0.75x | 0.185% / 0.013% |
| 2026-06-04 10:15 | 8.62x | Full-bodied bullish | Flat / fading | 0.000% / -0.072% / -0.171% | Position building in range | 62.7% | 35.6% | 1.7% | 3.70x | 0.138% / 0.178% |
| 2026-06-04 14:00 | 4.47x | Full-bodied bullish | Flat / fading | -0.198% / -0.264% / -0.277% | Position building in range | 65.6% | 27.8% | 6.7% | 3.83x | 0.073% / 0.303% |
| 2026-06-04 16:45 | 4.01x | Full-bodied bearish | Impulse / continuation | 0.099% / 0.046% / -0.259% | True breakout | 65.9% | 4.5% | 29.5% | 1.51x | 0.298% / 0.113% |
| 2026-06-04 17:45 | 3.58x | Full-bodied bearish | Flat / fading | 0.100% / 0.100% / 0.140% | Weak move without breakout | 85.0% | 0.0% | 15.0% | 1.58x | 0.047% / 0.166% |
| 2026-06-04 19:15 | 4.63x | Small-body bearish | Flat / fading | -0.007% / 0.027% / 0.000% | Position building in range | 46.4% | 16.1% | 37.5% | 2.57x | 0.113% / 0.027% |
| 2026-06-05 09:00 | 3.58x | Full-bodied bearish | Flat / fading | 0.000% / 0.120% / 0.000% | Position building in range | 64.7% | 11.8% | 23.5% | 2.87x | 0.067% / 0.160% |
| 2026-06-05 10:15 | 3.05x | Doji | Impulse / continuation | 0.007% / 0.020% / -0.227% | True breakout | 0.0% | 43.7% | 56.3% | 0.72x | 0.247% / 0.247% |
| 2026-06-05 11:15 | 4.85x | Full-bodied bearish | Flat / fading | 0.080% / 0.167% / 0.100% | Position building in range | 93.5% | 0.0% | 6.5% | 2.21x | -0.013% / 0.207% |
| 2026-06-05 16:45 | 6.80x | Bullish pin-bar / lower rejection | Flat / fading | -0.114% / -0.053% / -0.167% | Position building in range | 17.3% | 0.0% | 82.7% | 4.26x | 0.167% / 0.033% |
| 2026-06-05 18:15 | 12.19x | Bullish pin-bar / lower rejection | Flat / fading | -0.040% / -0.081% / -0.020% | Position building in range | 35.6% | 6.9% | 57.5% | 5.56x | 0.295% / 0.087% |
| 2026-06-06 18:30 | 4.77x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.000% / -0.047% / 0.040% | False breakout | 12.5% | 50.0% | 37.5% | 2.38x | 0.350% / 0.047% |
| 2026-06-07 10:00 | 5.83x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.040% / 0.027% / 0.121% | True breakout | 11.3% | 1.9% | 86.8% | 12.79x | 0.121% / 0.013% |
| 2026-06-07 12:00 | 2.83x | Doji / lower rejection | Flat / fading | -0.007% / -0.013% / -0.061% | Weak move without breakout | 0.0% | 10.0% | 90.0% | 0.99x | 0.114% / 0.114% |
| 2026-06-07 16:15 | 4.23x | Doji / upper rejection | Impulse / continuation | 0.000% / 0.067% / 0.034% | True breakout | 0.0% | 80.0% | 20.0% | 0.89x | 0.087% / 0.087% |
| 2026-06-07 16:45 | 4.05x | Full-bodied bullish | Flat / fading | 0.000% / -0.034% / 0.000% | Weak move without breakout | 90.0% | 0.0% | 10.0% | 2.30x | 0.020% / 0.040% |
| 2026-06-08 07:00 | 17.38x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.161% / 0.147% / 0.094% | True breakout | 26.9% | 69.2% | 3.8% | 3.14x | 0.215% / 0.000% |
| 2026-06-08 07:15 | 12.16x | Full-bodied bullish | Flat / fading | -0.013% / -0.047% / -0.067% | Position building in range | 75.0% | 25.0% | 0.0% | 3.18x | 0.013% / 0.107% |
| 2026-06-08 08:00 | 3.86x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.000% / -0.047% / -0.114% | True breakout | 20.0% | 40.0% | 40.0% | 1.16x | 0.147% / 0.054% |
| 2026-06-08 09:00 | 2.65x | Full-bodied bearish | Impulse / continuation | -0.040% / 0.067% / -0.261% | True breakout | 60.0% | 15.0% | 25.0% | 1.37x | 0.349% / 0.107% |
| 2026-06-08 09:15 | 3.33x | Small-body bearish | Reversal | 0.107% / 0.027% / -0.215% | Liquidity sweep / reversal | 37.5% | 25.0% | 37.5% | 1.03x | 0.309% / 0.148% |
| 2026-06-08 09:30 | 2.90x | Full-bodied bullish | Reversal | -0.080% / -0.328% / -0.570% | Liquidity sweep / reversal | 66.7% | 25.0% | 8.3% | 1.49x | 0.000% / 0.670% |
| 2026-06-08 10:00 | 5.55x | Full-bodied bearish | Impulse / continuation | 0.007% / -0.242% / -0.027% | True breakout | 70.7% | 6.9% | 22.4% | 3.48x | 0.343% / 0.094% |
| 2026-06-08 10:30 | 6.94x | Full-bodied bearish | Impulse / continuation | 0.243% / 0.216% / -0.182% | True breakout | 62.3% | 13.1% | 24.6% | 3.11x | 0.445% / 0.283% |
| 2026-06-08 11:30 | 3.78x | Bullish pin-bar / lower rejection | Flat / fading | -0.020% / -0.162% / -0.263% | Weak move without breakout | 45.7% | 6.2% | 48.1% | 3.06x | 0.351% / 0.034% |
| 2026-06-08 15:15 | 4.05x | Full-bodied bearish | Impulse / continuation | -0.287% / -0.315% / -0.944% | True breakout | 82.6% | 4.7% | 12.8% | 3.01x | 0.957% / 0.116% |
| 2026-06-08 15:30 | 4.06x | Small-body bearish | Impulse / continuation | -0.027% / -0.281% / -0.343% | True breakout | 54.7% | 24.0% | 21.3% | 2.40x | 0.795% / 0.075% |
| 2026-06-08 15:45 | 6.67x | Bullish pin-bar / lower rejection | Flat / fading | -0.254% / -0.631% / -0.226% | Weak move without breakout | 2.1% | 13.4% | 84.5% | 2.80x | 0.768% / 0.048% |
| 2026-06-09 07:00 | 2.65x | Full-bodied bearish | Flat / fading | 0.131% / 0.089% / 0.034% | Weak move without breakout | 87.5% | 2.1% | 10.4% | 1.95x | 0.131% / 0.172% |
| 2026-06-09 08:00 | 2.61x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.089% / 0.069% / 0.296% | False breakout | 6.9% | 17.2% | 75.9% | 1.17x | 0.529% / 0.172% |
| 2026-06-09 09:00 | 6.82x | Small-body bullish | Flat / fading | -0.062% / -0.014% / -0.110% | Position building in range | 50.0% | 33.3% | 16.7% | 4.29x | 0.089% / 0.281% |
| 2026-06-09 10:15 | 11.43x | Full-bodied bearish | Impulse / continuation | -0.887% / 0.305% / 0.305% | True breakout | 94.6% | 0.0% | 5.4% | 4.03x | 1.053% / 0.644% |
| 2026-06-09 10:30 | 12.43x | Full-bodied bearish | Reversal | 1.202% / 1.377% / 1.251% | Liquidity sweep / reversal | 90.1% | 4.3% | 5.7% | 3.08x | 0.168% / 1.545% |
| 2026-06-09 10:45 | 9.52x | Full-bodied bullish | Flat / fading | 0.173% / 0.000% / 0.062% | Weak move without breakout | 83.9% | 4.4% | 11.7% | 3.92x | 0.338% / 0.159% |
| 2026-06-09 16:30 | 2.58x | Full-bodied bullish | Impulse / continuation | 0.324% / 0.196% / 0.202% | True breakout | 81.5% | 18.5% | 0.0% | 1.35x | 0.499% / 0.020% |
| 2026-06-10 09:00 | 2.78x | Full-bodied bearish | Impulse / continuation | -0.101% / -0.175% / -0.452% | True breakout | 67.5% | 2.5% | 30.0% | 1.90x | 0.452% / 0.007% |
| 2026-06-10 09:15 | 4.15x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.074% / -0.169% / -0.243% | True breakout | 35.6% | 0.0% | 64.4% | 1.96x | 0.486% / 0.108% |
| 2026-06-10 09:45 | 3.00x | Bullish pin-bar / lower rejection | Reversal | -0.183% / -0.074% / 0.291% | Liquidity sweep / reversal | 33.3% | 7.7% | 59.0% | 1.49x | 0.318% / 0.406% |
| 2026-06-10 10:00 | 2.75x | Full-bodied bearish | Reversal | 0.108% / 0.352% / -0.278% | Liquidity sweep / reversal | 90.0% | 10.0% | 0.0% | 1.09x | 0.312% / 0.590% |
| 2026-06-10 10:15 | 5.88x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.244% / 0.366% / -0.386% | False breakout | 23.3% | 40.0% | 36.7% | 2.08x | 0.481% / 0.596% |
| 2026-06-10 10:30 | 3.22x | Small-body bullish | Reversal | 0.122% / -0.628% / -0.466% | Liquidity sweep / reversal | 56.9% | 23.1% | 20.0% | 1.99x | 0.236% / 0.837% |
| 2026-06-10 10:45 | 2.87x | Bearish pin-bar / upper rejection | Reversal | -0.749% / -0.749% / -0.418% | Liquidity sweep / reversal | 42.9% | 40.5% | 16.7% | 1.16x | 0.000% / 0.958% |
| 2026-06-10 11:00 | 3.49x | Full-bodied bearish | Flat / fading | 0.000% / 0.163% / 0.421% | Weak move without breakout | 94.8% | 0.9% | 4.3% | 3.23x | 0.211% / 0.442% |
| 2026-06-10 13:00 | 3.11x | Full-bodied bullish | Flat / fading | -0.269% / -0.443% / -0.275% | Position building in range | 76.8% | 14.3% | 8.9% | 2.53x | 0.094% / 0.578% |
| 2026-06-10 14:45 | 1.99x | Full-bodied bearish | Impulse / continuation | -0.231% / -0.244% / -0.156% | True breakout | 86.6% | 3.7% | 9.8% | 1.80x | 0.821% / 0.075% |
| 2026-06-10 15:00 | 2.88x | Bullish pin-bar / lower rejection | Flat / fading | -0.014% / 0.109% / 0.190% | Weak move without breakout | 27.5% | 0.0% | 72.5% | 2.46x | 0.258% / 0.306% |
| 2026-06-10 17:45 | 4.06x | Full-bodied bullish | Flat / fading | 0.020% / -0.293% / -0.633% | Position building in range | 79.2% | 20.8% | 0.0% | 2.96x | 0.160% / 0.633% |
| 2026-06-11 08:00 | 5.13x | Small-body bullish | Flat / fading | -0.007% / 0.114% / -0.074% | Position building in range | 55.4% | 33.0% | 11.6% | 4.67x | 0.114% / 0.168% |
| 2026-06-11 10:00 | 2.54x | Bullish pin-bar / lower rejection | Reversal | -0.074% / 0.020% / 0.275% | Liquidity sweep / reversal | 12.9% | 32.3% | 54.8% | 1.00x | 0.315% / 0.416% |
| 2026-06-11 11:00 | 4.45x | Full-bodied bullish | Flat / fading | -0.248% / -0.134% / 0.107% | Weak move without breakout | 72.0% | 22.6% | 5.4% | 2.76x | 0.228% / 0.361% |
| 2026-06-11 23:30 | 2.69x | Full-bodied bearish | Reversal | 0.074% / 0.081% / 0.047% | Liquidity sweep / reversal | 64.0% | 20.0% | 16.0% | 1.33x | 0.223% / 0.149% |
| 2026-06-12 16:45 | 16.63x | Bullish pin-bar / lower rejection | Flat / fading | 0.014% / -0.007% / -0.034% | Position building in range | 24.0% | 0.0% | 76.0% | 5.38x | 0.081% / 0.014% |
| 2026-06-13 10:00 | 2.54x | Bearish pin-bar / upper rejection | Reversal | -0.034% / -0.047% / -0.047% | Liquidity sweep / reversal | 27.3% | 50.0% | 22.7% | 2.80x | 0.000% / 0.068% |
| 2026-06-13 18:30 | 3.34x | Bullish pin-bar / lower rejection | Reversal | 0.014% / 0.014% / 0.054% | Liquidity sweep / reversal | 16.7% | 16.7% | 66.7% | 1.75x | 0.054% / 0.068% |
| 2026-06-13 18:45 | 3.15x | Small-body bullish | Impulse / continuation | 0.000% / 0.027% / 0.034% | True breakout | 33.3% | 33.3% | 33.3% | 1.75x | 0.054% / 0.068% |
| 2026-06-14 10:00 | 4.94x | Bullish pin-bar / lower rejection | Flat / fading | 0.014% / 0.007% / -0.014% | Position building in range | 22.2% | 22.2% | 55.6% | 5.36x | 0.020% / 0.014% |
| 2026-06-14 18:45 | 64.91x | Full-bodied bullish | Impulse / continuation | 0.303% / 0.667% / 0.512% | True breakout | 97.6% | 2.4% | 0.0% | 29.05x | 0.795% / -0.209% |
| 2026-06-15 07:00 | 20.05x | Full-bodied bullish | Flat / fading | -0.100% / -0.154% / -0.033% | Weak move without breakout | 62.4% | 20.0% | 17.6% | 7.30x | 0.127% / 0.281% |
| 2026-06-15 07:15 | 4.59x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.054% / -0.087% / 0.040% | True breakout | 30.6% | 63.9% | 5.6% | 2.07x | 0.181% / 0.167% |
| 2026-06-15 09:00 | 3.60x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.033% / 0.234% / 0.790% | True breakout | 36.5% | 11.5% | 51.9% | 1.88x | 0.810% / 0.120% |
| 2026-06-15 09:30 | 3.15x | Full-bodied bullish | Impulse / continuation | 0.220% / 0.554% / 0.294% | True breakout | 72.7% | 18.2% | 9.1% | 1.69x | 0.694% / 0.174% |
| 2026-06-15 09:45 | 3.54x | Full-bodied bullish | Impulse / continuation | 0.333% / 0.100% / 0.180% | True breakout | 61.0% | 0.0% | 39.0% | 1.63x | 0.473% / 0.107% |
| 2026-06-15 10:00 | 7.09x | Full-bodied bullish | Flat / fading | -0.232% / -0.259% / -0.219% | Weak move without breakout | 75.4% | 4.3% | 20.3% | 1.71x | 0.139% / 0.319% |
| 2026-06-15 10:15 | 4.54x | Full-bodied bearish | Flat / fading | -0.027% / 0.080% / -0.020% | Weak move without breakout | 62.5% | 37.5% | 0.0% | 1.43x | 0.087% / 0.106% |
| 2026-06-15 16:45 | 2.66x | Full-bodied bullish | Reversal | -0.053% / -0.316% / -0.428% | Liquidity sweep / reversal | 96.2% | 3.8% | 0.0% | 1.80x | 0.086% / 0.514% |
| 2026-06-16 09:00 | 3.32x | Bullish pin-bar / lower rejection | Flat / fading | 0.007% / -0.086% / -0.092% | Weak move without breakout | 52.9% | 0.0% | 47.1% | 1.66x | 0.165% / 0.007% |
| 2026-06-16 12:45 | 3.79x | Small-body bearish | Flat / fading | 0.073% / 0.000% / -0.026% | Position building in range | 51.3% | 25.0% | 23.7% | 3.58x | 0.086% / 0.179% |
| 2026-06-16 15:30 | 5.38x | Small-body bearish | Impulse / continuation | -0.214% / 0.073% / -0.601% | True breakout | 53.2% | 35.5% | 11.3% | 4.42x | 0.861% / 0.280% |
| 2026-06-16 15:45 | 3.25x | Full-bodied bearish | Reversal | 0.288% / 0.241% / -0.301% | Liquidity sweep / reversal | 65.3% | 0.0% | 34.7% | 1.37x | 0.649% / 0.495% |
| 2026-06-16 16:30 | 4.83x | Full-bodied bearish | Flat / fading | 0.087% / 0.020% / 0.208% | Position building in range | 70.9% | 0.0% | 29.1% | 3.36x | 0.262% / 0.249% |
| 2026-06-17 07:00 | 3.44x | Bullish pin-bar / lower rejection | Reversal | -0.228% / -0.154% / -0.335% | Liquidity sweep / reversal | 14.7% | 26.5% | 58.8% | 3.07x | 0.020% / 0.530% |
| 2026-06-17 07:45 | 3.71x | Full-bodied bearish | Reversal | 0.101% / 0.303% / 0.310% | Liquidity sweep / reversal | 74.5% | 0.0% | 25.5% | 3.32x | 0.061% / 0.398% |
| 2026-06-17 08:15 | 2.91x | Full-bodied bullish | Reversal | 0.034% / 0.007% / -0.222% | Liquidity sweep / reversal | 75.7% | 8.1% | 16.2% | 1.74x | 0.094% / 0.289% |
| 2026-06-17 10:30 | 5.64x | Full-bodied bullish | Impulse -> reversal | 0.208% / 0.067% / -0.455% | False breakout | 67.8% | 23.7% | 8.5% | 1.88x | 0.382% / 0.502% |
| 2026-06-17 10:45 | 3.91x | Small-body bullish | Reversal | -0.140% / -0.020% / -0.982% | Liquidity sweep / reversal | 44.3% | 37.1% | 18.6% | 2.11x | 0.120% / 1.096% |
| 2026-06-17 11:45 | 3.21x | Full-bodied bearish | Flat / fading | -0.034% / -0.094% / 0.108% | Weak move without breakout | 70.8% | 3.1% | 26.2% | 1.59x | 0.263% / 0.223% |
| 2026-06-18 07:00 | 5.41x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.122% / -0.027% / -0.047% | False breakout | 1.9% | 17.3% | 80.8% | 3.79x | 0.155% / 0.149% |
| 2026-06-18 09:00 | 6.94x | Full-bodied bearish | Impulse / continuation | -0.325% / -0.332% / -0.426% | True breakout | 72.2% | 5.6% | 22.2% | 0.98x | 0.474% / 0.027% |
| 2026-06-18 09:15 | 6.39x | Full-bodied bearish | Impulse / continuation | -0.007% / -0.048% / -0.183% | True breakout | 70.1% | 7.5% | 22.4% | 3.53x | 0.761% / 0.115% |
| 2026-06-18 10:15 | 9.86x | Bullish pin-bar / lower rejection | Flat / fading | -0.374% / -0.340% / -0.211% | Position building in range | 12.6% | 4.9% | 82.5% | 4.12x | 0.524% / 0.000% |
| 2026-06-18 10:30 | 5.95x | Full-bodied bearish | Flat / fading | 0.034% / 0.048% / 0.171% | Weak move without breakout | 77.6% | 4.5% | 17.9% | 2.12x | 0.150% / 0.328% |
| 2026-06-18 10:45 | 2.74x | Bullish pin-bar / lower rejection | Flat / fading | 0.014% / 0.130% / 0.109% | Weak move without breakout | 14.0% | 37.2% | 48.8% | 1.31x | 0.294% / 0.164% |
| 2026-06-18 14:45 | 2.48x | Bearish pin-bar / upper rejection | Flat / fading | 0.041% / 0.103% / 0.138% | Weak move without breakout | 11.5% | 48.1% | 40.4% | 1.54x | 0.262% / 0.393% |
| 2026-06-18 15:00 | 2.79x | Bullish pin-bar / lower rejection | Reversal | 0.062% / -0.062% / 0.358% | Liquidity sweep / reversal | 9.5% | 0.0% | 90.5% | 1.93x | 0.427% / 0.193% |
| 2026-06-19 07:00 | 2.98x | Small-body bullish | Impulse / continuation | 0.069% / 0.089% / 0.254% | True breakout | 44.0% | 22.0% | 34.0% | 3.02x | 0.364% / 0.137% |
| 2026-06-19 09:00 | 3.71x | Bearish pin-bar / upper rejection | Reversal | -0.514% / -0.390% / -0.349% | Liquidity sweep / reversal | 58.7% | 41.3% | 0.0% | 2.18x | 0.000% / 1.500% |
| 2026-06-19 09:15 | 17.84x | Bullish pin-bar / lower rejection | Flat / fading | 0.124% / 0.227% / 0.000% | Position building in range | 34.2% | 0.0% | 65.8% | 6.87x | 0.289% / 0.344% |
| 2026-06-19 13:30 | 18.78x | Full-bodied bearish | Flat / fading | 0.078% / 0.042% / 0.183% | Position building in range | 75.9% | 0.0% | 24.1% | 12.58x | 0.360% / 0.367% |
| 2026-06-19 23:15 | 4.49x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.603% / -0.433% / -0.050% | True breakout | 56.0% | 1.2% | 42.9% | 3.34x | 0.767% / 0.106% |
| 2026-06-19 23:30 | 5.22x | Full-bodied bearish | Reversal | 0.171% / 0.521% / 0.679% | Liquidity sweep / reversal | 93.3% | 5.6% | 1.1% | 3.05x | 0.164% / 0.750% |
| 2026-06-22 09:00 | 2.72x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.347% / -0.007% / -0.092% | True breakout | 53.7% | 6.1% | 40.2% | 1.95x | 0.354% / 0.439% |
| 2026-06-22 09:45 | 4.33x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.149% / -0.291% / 0.873% | False breakout | 50.0% | 4.8% | 45.2% | 1.32x | 0.653% / 1.015% |
| 2026-06-22 10:30 | 3.85x | Small-body bullish | Impulse / continuation | 0.844% / 0.887% / 0.496% | True breakout | 32.1% | 29.9% | 38.0% | 2.71x | 0.986% / 0.043% |
| 2026-06-22 10:45 | 3.79x | Full-bodied bullish | Flat / fading | 0.042% / -0.345% / -0.366% | Position building in range | 82.8% | 13.8% | 3.4% | 2.58x | 0.077% / 0.513% |
| 2026-06-22 12:45 | 2.43x | Full-bodied bearish | Reversal | 0.114% / 0.000% / 0.493% | Liquidity sweep / reversal | 64.0% | 18.7% | 17.3% | 1.05x | 0.007% / 0.971% |
| 2026-06-22 14:00 | 1.94x | Small-body bullish | Reversal | -0.686% / -0.566% / -1.909% | Liquidity sweep / reversal | 55.4% | 13.8% | 30.8% | 1.78x | 0.007% / 2.390% |
| 2026-06-22 14:45 | 3.99x | Full-bodied bearish | Impulse / continuation | 0.072% / -0.245% / 0.159% | True breakout | 90.6% | 4.9% | 4.5% | 3.23x | 0.700% / 0.346% |
| 2026-06-22 15:00 | 2.44x | Bullish pin-bar / lower rejection | Reversal | -0.317% / -0.108% / 0.173% | Liquidity sweep / reversal | 9.4% | 35.8% | 54.7% | 1.33x | 0.245% / 0.771% |
| 2026-06-22 22:00 | 3.13x | Full-bodied bearish | Impulse / continuation | -0.015% / 0.362% / 1.297% | True breakout | 89.0% | 8.0% | 3.0% | 3.26x | 1.402% / 1.440% |
| 2026-06-22 22:15 | 3.89x | Bearish pin-bar / upper rejection | Reversal | 0.377% / 1.229% / 1.628% | Liquidity sweep / reversal | 1.4% | 78.9% | 19.7% | 1.01x | 1.387% / 2.209% |
| 2026-06-22 22:30 | 4.90x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.849% / 0.931% / 1.450% | True breakout | 20.9% | 7.5% | 71.5% | 3.50x | 1.825% / 0.285% |
| 2026-06-24 07:00 | 6.77x | Small-body bullish | Flat / fading | -0.036% / 0.065% / 0.086% | Position building in range | 41.6% | 31.0% | 27.4% | 4.63x | 0.216% / 0.122% |
| 2026-06-24 07:15 | 2.72x | Bearish pin-bar / upper rejection | Reversal | 0.101% / 0.043% / 0.469% | Liquidity sweep / reversal | 12.8% | 61.7% | 25.5% | 1.62x | 0.079% / 0.699% |
| 2026-06-24 08:15 | 4.24x | Bearish pin-bar / upper rejection | Reversal | -0.115% / -0.323% / -0.940% | Liquidity sweep / reversal | 60.0% | 40.0% | 0.0% | 2.51x | 0.065% / 1.105% |
| 2026-06-24 08:30 | 2.53x | Small-body bearish | Impulse / continuation | -0.208% / -0.431% / -0.725% | True breakout | 51.6% | 29.0% | 19.4% | 0.90x | 0.991% / 0.000% |
| 2026-06-24 09:00 | 2.67x | Small-body bearish | Impulse / continuation | -0.397% / -0.296% / -0.635% | True breakout | 51.6% | 17.7% | 30.6% | 1.78x | 0.931% / 0.115% |
| 2026-06-24 09:15 | 5.72x | Small-body bearish | Impulse / continuation | 0.101% / -0.058% / -0.348% | True breakout | 57.4% | 18.1% | 24.5% | 2.45x | 0.536% / 0.355% |
| 2026-06-24 10:00 | 2.65x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.109% / -0.261% / -0.232% | True breakout | 34.4% | 1.6% | 64.1% | 1.30x | 0.857% / 0.595% |
| 2026-06-24 10:15 | 5.38x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.153% / -0.661% / -0.320% | True breakout | 15.2% | 82.8% | 2.0% | 1.89x | 0.749% / 0.225% |
| 2026-06-24 10:30 | 2.57x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.510% / 0.029% / -0.167% | True breakout | 34.8% | 40.6% | 24.6% | 1.19x | 0.597% / 0.160% |
| 2026-06-24 10:45 | 3.17x | Full-bodied bearish | Reversal | 0.541% / 0.344% / 0.212% | Liquidity sweep / reversal | 67.3% | 21.2% | 11.5% | 1.89x | 0.088% / 0.658% |
| 2026-06-24 17:30 | 5.41x | Full-bodied bearish | Impulse / continuation | -1.539% / -0.699% / -1.621% | True breakout | 61.2% | 10.7% | 28.2% | 2.05x | 1.807% / 0.015% |
| 2026-06-24 17:45 | 3.81x | Full-bodied bearish | Flat / fading | 0.853% / 0.513% / 0.513% | Position building in range | 84.9% | 0.4% | 14.7% | 4.43x | 0.166% / 1.050% |
| 2026-06-24 19:00 | 2.83x | Small-body bullish | Flat / fading | 0.223% / -0.439% / -0.633% | Weak move without breakout | 57.1% | 18.9% | 24.1% | 2.64x | 0.387% / 0.789% |
| 2026-06-25 07:00 | 2.62x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.380% / 0.037% / -0.082% | True breakout | 17.2% | 16.4% | 66.4% | 4.47x | 0.409% / 0.439% |
| 2026-06-25 09:00 | 5.34x | Small-body bearish | Reversal | 0.658% / 0.957% / 1.525% | Liquidity sweep / reversal | 39.1% | 28.3% | 32.6% | 2.18x | 0.000% / 1.607% |
| 2026-06-25 09:15 | 4.37x | Full-bodied bullish | Impulse / continuation | 0.297% / 0.364% / 0.282% | True breakout | 92.6% | 7.4% | 0.0% | 2.00x | 1.069% / 0.193% |
| 2026-06-25 09:30 | 4.98x | Small-body bullish | Impulse / continuation | 0.067% / 0.563% / 0.207% | True breakout | 39.2% | 35.3% | 25.5% | 1.94x | 0.770% / 0.244% |
| 2026-06-25 10:00 | 2.64x | Full-bodied bullish | Reversal | -0.574% / -0.353% / 0.037% | Liquidity sweep / reversal | 62.6% | 10.3% | 27.1% | 1.76x | 0.206% / 0.979% |
| 2026-06-25 10:45 | 2.66x | Full-bodied bearish | Reversal | 0.928% / 0.676% / 0.260% | Liquidity sweep / reversal | 82.6% | 2.3% | 15.1% | 1.22x | 0.000% / 1.478% |
| 2026-06-25 11:00 | 3.06x | Full-bodied bullish | Flat / fading | -0.250% / -0.478% / -0.228% | Weak move without breakout | 85.5% | 13.8% | 0.7% | 2.01x | 0.545% / 0.832% |
| 2026-06-25 13:15 | 2.36x | Full-bodied bearish | Flat / fading | 0.520% / 0.603% / -0.286% | Weak move without breakout | 66.2% | 12.0% | 21.8% | 1.59x | 0.753% / 1.168% |
| 2026-06-26 10:15 | 2.55x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.151% / -0.038% / -0.664% | True breakout | 6.4% | 79.3% | 14.3% | 2.35x | 0.747% / 0.241% |
| 2026-06-26 12:30 | 3.05x | Full-bodied bullish | Reversal | -0.181% / -0.858% / -1.346% | Liquidity sweep / reversal | 83.8% | 16.2% | 0.0% | 1.37x | 0.000% / 1.422% |
| 2026-06-26 14:15 | 1.98x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.549% / 1.205% / 2.625% | True breakout | 7.8% | 10.9% | 81.3% | 0.89x | 3.227% / -0.008% |
| 2026-06-26 14:30 | 1.76x | Full-bodied bullish | Impulse / continuation | 0.653% / 2.011% / 2.876% | True breakout | 61.7% | 38.3% | 0.0% | 1.67x | 3.384% / 0.364% |
| 2026-06-26 14:45 | 2.22x | Small-body bullish | Impulse / continuation | 1.349% / 1.402% / 3.053% | True breakout | 58.1% | 9.5% | 32.4% | 2.07x | 3.445% / 0.475% |
| 2026-06-26 15:00 | 6.02x | Small-body bullish | Impulse / continuation | 0.052% / 0.848% / 0.558% | True breakout | 55.2% | 26.2% | 18.6% | 4.34x | 2.068% / 0.699% |
| 2026-06-26 15:30 | 3.09x | Full-bodied bullish | Flat / fading | 0.826% / -0.288% / -0.561% | Weak move without breakout | 60.9% | 38.5% | 0.6% | 1.71x | 1.210% / 0.959% |
| 2026-06-26 15:45 | 2.72x | Small-body bullish | Reversal | -1.105% / -1.302% / -1.587% | Liquidity sweep / reversal | 41.2% | 19.1% | 39.7% | 2.46x | 0.285% / 1.770% |
| 2026-06-27 18:45 | 2.90x | Bearish pin-bar / upper rejection | Reversal | 0.068% / 0.151% / 0.098% | Liquidity sweep / reversal | 21.4% | 71.4% | 7.1% | 1.69x | -0.038% / 0.173% |
| 2026-06-28 10:00 | 2.68x | Small-body bullish | Flat / fading | 0.015% / -0.053% / -0.038% | Weak move without breakout | 55.6% | 16.7% | 27.8% | 2.00x | 0.023% / 0.143% |
| 2026-06-28 11:00 | 5.06x | Bullish pin-bar / lower rejection | Flat / fading | 0.038% / 0.030% / -0.038% | Position building in range | 25.0% | 30.0% | 45.0% | 1.99x | 0.045% / 0.075% |
| 2026-06-28 16:15 | 3.38x | Full-bodied bearish | Impulse -> reversal | -0.015% / 0.120% / 0.120% | False breakout | 61.1% | 38.9% | 0.0% | 2.21x | 0.068% / 0.143% |
| 2026-06-28 16:45 | 2.65x | Full-bodied bullish | Flat / fading | -0.023% / 0.000% / -0.008% | Position building in range | 81.8% | 13.6% | 4.5% | 2.43x | 0.008% / 0.075% |
| 2026-06-29 07:00 | 11.10x | Bearish pin-bar / upper rejection | Reversal | 0.120% / 0.075% / 0.045% | Liquidity sweep / reversal | 41.7% | 50.0% | 8.3% | 3.63x | 0.053% / 0.135% |
| 2026-06-29 07:30 | 3.76x | Bullish pin-bar / lower rejection | Flat / fading | -0.113% / -0.030% / 0.038% | Weak move without breakout | 26.1% | 0.0% | 73.9% | 1.77x | 0.128% / 0.075% |
| 2026-06-29 09:00 | 4.84x | Full-bodied bearish | Impulse / continuation | -0.226% / -0.166% / -0.196% | True breakout | 91.5% | 1.7% | 6.8% | 3.90x | 0.415% / 0.008% |
| 2026-06-29 09:15 | 9.72x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.060% / 0.068% / -0.257% | True breakout | 55.4% | 0.0% | 44.6% | 2.93x | 0.340% / 0.181% |
| 2026-06-29 09:30 | 3.91x | Bullish pin-bar / lower rejection | Reversal | 0.008% / -0.030% / -0.831% | Liquidity sweep / reversal | 22.0% | 24.4% | 53.7% | 1.79x | 0.121% / 0.854% |
| 2026-06-29 10:15 | 2.89x | Full-bodied bearish | Impulse -> reversal | -0.516% / -0.349% / 0.887% | False breakout | 76.6% | 0.0% | 23.4% | 1.60x | 0.690% / 0.963% |
| 2026-06-29 10:30 | 3.91x | Full-bodied bearish | Reversal | 0.168% / 0.808% / 2.042% | Liquidity sweep / reversal | 63.1% | 34.0% | 2.9% | 3.28x | 0.175% / 2.370% |
| 2026-06-29 10:45 | 2.64x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.639% / 1.240% / 2.138% | True breakout | 48.9% | 0.0% | 51.1% | 1.24x | 2.199% / 0.038% |
| 2026-06-29 11:00 | 6.36x | Full-bodied bullish | Impulse / continuation | 0.597% / 1.225% / 1.625% | True breakout | 64.9% | 32.1% | 3.1% | 3.47x | 1.890% / 0.000% |
| 2026-06-29 11:15 | 4.87x | Full-bodied bullish | Impulse / continuation | 0.624% / 0.887% / 1.007% | True breakout | 87.6% | 11.2% | 1.1% | 1.96x | 1.285% / 0.000% |
| 2026-06-29 11:30 | 3.90x | Full-bodied bullish | Flat / fading | 0.261% / 0.396% / -0.119% | Weak move without breakout | 65.1% | 34.1% | 0.8% | 2.49x | 0.657% / 0.261% |
| 2026-06-30 08:15 | 2.89x | Full-bodied bullish | Reversal | -0.345% / -0.360% / -0.602% | Liquidity sweep / reversal | 84.0% | 8.0% | 8.0% | 1.49x | 0.184% / 0.631% |
| 2026-06-30 12:15 | 6.18x | Full-bodied bullish | Flat / fading | 0.160% / 0.203% / -0.015% | Weak move without breakout | 74.6% | 19.6% | 5.8% | 2.65x | 0.501% / 0.160% |
| 2026-07-01 07:00 | 3.14x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.044% / 0.125% | Liquidity sweep / reversal | 21.2% | 51.9% | 26.9% | 2.19x | 0.198% / 0.316% |
| 2026-07-01 08:15 | 4.57x | Full-bodied bullish | Impulse / continuation | -0.124% / -0.102% / 0.080% | True breakout | 82.5% | 17.5% | 0.0% | 3.86x | 0.314% / 0.292% |
| 2026-07-01 09:00 | 3.99x | Small-body bullish | Reversal | -0.051% / -0.270% / -0.044% | Liquidity sweep / reversal | 40.0% | 31.2% | 28.8% | 2.53x | 0.168% / 0.495% |
| 2026-07-01 09:45 | 2.73x | Small-body bullish | Reversal | 0.088% / -0.161% / -0.591% | Liquidity sweep / reversal | 34.0% | 30.2% | 35.8% | 1.30x | 0.146% / 0.642% |
| 2026-07-01 11:00 | 2.85x | Small-body bullish | Reversal | -0.256% / -0.380% / -0.665% | Liquidity sweep / reversal | 48.7% | 20.0% | 31.3% | 2.18x | 0.007% / 0.892% |
| 2026-07-01 12:15 | 4.10x | Full-bodied bullish | Flat / fading | -0.204% / -0.429% / -0.342% | Position building in range | 82.9% | 16.6% | 0.5% | 3.12x | 0.116% / 0.655% |
| 2026-07-02 07:00 | 4.44x | Small-body bullish | Reversal | -0.110% / -0.088% / -0.044% | Liquidity sweep / reversal | 48.3% | 24.1% | 27.6% | 2.78x | 0.037% / 0.177% |
| 2026-07-02 08:15 | 3.15x | Full-bodied bearish | Impulse / continuation | 0.074% / 0.059% / -0.125% | True breakout | 94.6% | 2.7% | 2.7% | 2.73x | 0.266% / 0.288% |
| 2026-07-02 09:00 | 7.01x | Bearish pin-bar / upper rejection | Reversal | -0.221% / -0.214% / -0.605% | Liquidity sweep / reversal | 10.0% | 52.0% | 38.0% | 3.18x | 0.007% / 0.818% |
| 2026-07-02 09:15 | 3.97x | Full-bodied bearish | Impulse / continuation | 0.007% / -0.281% / -0.133% | True breakout | 62.0% | 0.0% | 38.0% | 2.72x | 0.598% / 0.103% |
| 2026-07-02 09:45 | 7.55x | Bullish pin-bar / lower rejection | Flat / fading | -0.104% / 0.148% / -0.030% | Position building in range | 45.2% | 3.6% | 51.2% | 3.96x | 0.156% / 0.267% |
| 2026-07-02 13:00 | 2.69x | Full-bodied bearish | Impulse / continuation | -0.344% / -0.486% / -0.291% | True breakout | 65.8% | 0.0% | 34.2% | 2.10x | 0.590% / 0.105% |
| 2026-07-02 14:30 | 2.77x | Full-bodied bearish | Impulse / continuation | -0.591% / -0.644% / -1.189% | True breakout | 85.7% | 9.5% | 4.8% | 2.45x | 1.576% / 0.023% |
| 2026-07-02 14:45 | 5.11x | Full-bodied bearish | Impulse / continuation | -0.053% / -0.930% / -0.884% | True breakout | 80.4% | 3.1% | 16.5% | 2.05x | 0.991% / 0.213% |
| 2026-07-02 15:00 | 2.96x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.877% / -0.549% / -0.793% | True breakout | 15.6% | 62.2% | 22.2% | 0.88x | 0.938% / 0.267% |
| 2026-07-02 15:15 | 6.36x | Full-bodied bearish | Flat / fading | 0.331% / 0.046% / 0.223% | Position building in range | 72.8% | 22.2% | 5.1% | 3.03x | 0.062% / 0.500% |
| 2026-07-02 15:30 | 2.61x | Full-bodied bullish | Flat / fading | -0.284% / -0.245% / -0.245% | Weak move without breakout | 63.2% | 25.0% | 11.8% | 1.11x | 0.169% / 0.330% |
| 2026-07-02 16:45 | 3.90x | Full-bodied bearish | Reversal | 0.611% / 0.650% / 0.898% | Liquidity sweep / reversal | 78.9% | 6.1% | 14.9% | 1.80x | 0.015% / 0.991% |
| 2026-07-03 08:30 | 4.18x | Full-bodied bearish | Flat / fading | 0.117% / 0.532% / 0.743% | Weak move without breakout | 82.9% | 0.0% | 17.1% | 2.97x | 0.211% / 1.040% |
| 2026-07-03 09:15 | 2.74x | Bearish pin-bar / upper rejection | Flat / fading | 0.085% / 0.179% / 0.412% | Weak move without breakout | 20.0% | 61.2% | 18.8% | 1.50x | 0.559% / 0.451% |
| 2026-07-03 10:45 | 7.73x | Full-bodied bearish | Flat / fading | 0.469% / 0.826% / 0.731% | Position building in range | 86.3% | 2.1% | 11.6% | 4.48x | 0.032% / 1.303% |
| 2026-07-03 11:00 | 2.93x | Small-body bullish | Flat / fading | 0.356% / 0.435% / -0.016% | Weak move without breakout | 58.3% | 38.8% | 2.9% | 1.26x | 0.830% / 0.332% |
| 2026-07-03 11:15 | 2.87x | Bearish pin-bar / upper rejection | Reversal | 0.079% / -0.095% / 0.016% | Liquidity sweep / reversal | 31.3% | 40.8% | 27.9% | 1.68x | 0.473% / 0.552% |
| 2026-07-03 14:30 | 2.96x | Small-body bullish | Flat / fading | -0.305% / -0.704% / -0.430% | Position building in range | 49.7% | 34.0% | 16.2% | 2.32x | 0.430% / 0.759% |
| 2026-07-04 11:45 | 2.70x | Bullish pin-bar / lower rejection | Reversal | -0.080% / 0.080% / 0.183% | Liquidity sweep / reversal | 9.3% | 7.0% | 83.7% | 1.56x | 0.191% / 0.088% |
| 2026-07-04 17:45 | 4.81x | Full-bodied bearish | Impulse / continuation | -0.040% / -0.096% / -0.080% | True breakout | 61.1% | 0.0% | 38.9% | 3.65x | 0.271% / 0.016% |
| 2026-07-04 18:30 | 5.68x | Bullish pin-bar / lower rejection | Reversal | 0.096% / 0.926% / 1.189% | Liquidity sweep / reversal | 41.7% | 8.3% | 50.0% | 3.39x | 0.048% / 1.333% |
| 2026-07-05 09:45 | 5.14x | Doji | Impulse / continuation | 0.024% / 0.261% / 0.190% | True breakout | 0.0% | 0.0% | 0.0% | 0.00x | 0.514% / 0.514% |
| 2026-07-05 10:00 | 23.73x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.237% / 0.190% / 0.134% | True breakout | 21.4% | 62.9% | 15.7% | 4.28x | 0.490% / 0.032% |
| 2026-07-05 10:15 | 4.44x | Full-bodied bullish | Flat / fading | -0.047% / -0.071% / -0.039% | Weak move without breakout | 65.4% | 34.6% | 0.0% | 2.48x | 0.252% / 0.260% |
| 2026-07-05 10:30 | 3.52x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.024% / -0.055% / -0.032% | True breakout | 17.9% | 79.5% | 2.6% | 1.61x | 0.213% / 0.063% |
| 2026-07-06 07:00 | 7.11x | Bearish pin-bar / upper rejection | Flat / fading | 0.071% / 0.063% / -0.142% | Weak move without breakout | 30.5% | 45.1% | 24.4% | 4.69x | 0.189% / 0.213% |
| 2026-07-06 07:30 | 2.64x | Doji | Impulse / continuation | -0.008% / -0.205% / -0.260% | True breakout | 0.0% | 47.5% | 52.5% | 1.74x | 0.386% / 0.386% |
| 2026-07-06 07:45 | 2.80x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.197% / -0.370% / -0.268% | True breakout | 4.5% | 72.7% | 22.7% | 0.90x | 0.378% / -0.016% |
| 2026-07-06 09:00 | 5.40x | Bearish pin-bar / upper rejection | Reversal | 0.214% / 0.523% / 0.404% | Liquidity sweep / reversal | 27.6% | 43.9% | 28.6% | 3.46x | 0.135% / 0.697% |
| 2026-07-06 09:15 | 3.69x | Small-body bullish | Impulse / continuation | 0.308% / 0.016% / 0.142% | True breakout | 49.2% | 32.2% | 18.6% | 1.72x | 0.482% / 0.348% |
| 2026-07-06 09:30 | 3.46x | Bullish pin-bar / lower rejection | Flat / fading | -0.291% / -0.118% / -0.299% | Position building in range | 37.1% | 21.0% | 41.9% | 2.89x | 0.118% / 0.496% |
| 2026-07-06 11:00 | 5.37x | Bearish pin-bar / upper rejection | Flat / fading | -0.180% / -0.416% / 0.094% | Weak move without breakout | 55.7% | 44.3% | 0.0% | 2.17x | 0.282% / 0.580% |
| 2026-07-06 12:00 | 2.11x | Full-bodied bullish | Reversal | -0.329% / -0.360% / -0.455% | Liquidity sweep / reversal | 76.7% | 21.9% | 1.4% | 1.25x | 0.063% / 0.737% |
| 2026-07-06 15:15 | 3.22x | Full-bodied bearish | Impulse / continuation | -0.158% / -0.237% / -0.950% | True breakout | 80.0% | 1.3% | 18.7% | 1.95x | 1.068% / 0.214% |
| 2026-07-06 16:00 | 5.05x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.334% / -1.840% / -2.142% | True breakout | 48.5% | 1.0% | 50.5% | 2.56x | 4.436% / 0.199% |
| 2026-07-06 16:15 | 3.97x | Small-body bearish | Impulse / continuation | -1.510% / -3.460% / -0.543% | True breakout | 51.2% | 30.5% | 18.3% | 1.94x | 4.115% / 0.008% |
| 2026-07-06 16:30 | 7.41x | Full-bodied bearish | Impulse / continuation | -1.980% / -0.308% / 0.763% | True breakout | 87.6% | 0.0% | 12.4% | 4.64x | 2.645% / 1.298% |
| 2026-07-06 16:45 | 8.19x | Full-bodied bearish | Reversal | 1.705% / 3.021% / 2.491% | Liquidity sweep / reversal | 62.3% | 16.8% | 20.9% | 6.76x | 0.166% / 3.344% |
| 2026-07-06 17:00 | 4.46x | Full-bodied bullish | Impulse / continuation | 1.294% / 1.074% / 0.854% | True breakout | 72.8% | 20.1% | 7.1% | 3.40x | 1.611% / 0.090% |
| 2026-07-07 08:15 | 3.45x | Full-bodied bearish | Impulse / continuation | -0.446% / 0.065% / -0.284% | True breakout | 62.8% | 0.0% | 37.2% | 4.75x | 0.770% / 0.162% |
| 2026-07-07 08:30 | 3.81x | Bullish pin-bar / lower rejection | Reversal | 0.513% / 0.391% / 0.399% | Liquidity sweep / reversal | 60.0% | 0.0% | 40.0% | 2.97x | 0.049% / 0.611% |
| 2026-07-07 09:00 | 3.49x | Bullish pin-bar / lower rejection | Reversal | -0.227% / 0.008% / 0.641% | Liquidity sweep / reversal | 20.0% | 18.6% | 61.4% | 1.74x | 0.333% / 0.876% |
| 2026-07-07 10:00 | 3.61x | Full-bodied bullish | Reversal | -0.387% / -0.468% / -1.371% | Liquidity sweep / reversal | 63.6% | 20.7% | 15.7% | 2.85x | 0.169% / 2.588% |
| 2026-07-07 10:45 | 5.22x | Full-bodied bearish | Flat / fading | 0.443% / 1.035% / 0.911% | Weak move without breakout | 80.2% | 0.0% | 19.8% | 3.44x | 0.796% / 1.297% |
| 2026-07-07 11:00 | 4.08x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.589% / 0.515% / 2.264% | True breakout | 35.7% | 1.9% | 62.3% | 2.06x | 2.796% / 0.065% |
| 2026-07-07 12:00 | 5.78x | Full-bodied bullish | Impulse / continuation | 1.007% / 1.711% / 1.902% | True breakout | 76.7% | 22.6% | 0.7% | 3.42x | 2.598% / 0.520% |
| 2026-07-07 12:15 | 2.63x | Full-bodied bullish | Impulse / continuation | 0.696% / 0.997% / 0.404% | True breakout | 60.0% | 6.8% | 33.2% | 2.10x | 1.575% / 0.127% |
| 2026-07-07 12:30 | 3.05x | Full-bodied bullish | Reversal | 0.299% / 0.189% / -0.857% | Liquidity sweep / reversal | 67.7% | 16.1% | 16.1% | 1.16x | 0.872% / 1.124% |
| 2026-07-07 13:00 | 2.37x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.479% / -1.043% / -0.133% | True breakout | 13.6% | 70.9% | 15.5% | 0.89x | 1.310% / 0.267% |
| 2026-07-08 09:00 | 4.09x | Full-bodied bearish | Impulse / continuation | -0.140% / -0.140% / -0.616% | True breakout | 100.0% | 0.0% | 0.0% | 2.45x | 0.764% / 0.109% |
| 2026-07-08 10:00 | 3.13x | Full-bodied bearish | Impulse / continuation | -0.361% / -0.376% / 0.102% | True breakout | 62.0% | 11.3% | 26.8% | 1.71x | 0.698% / 0.172% |
| 2026-07-08 10:15 | 2.82x | Small-body bearish | Reversal | -0.016% / 0.039% / 1.023% | Liquidity sweep / reversal | 48.4% | 23.2% | 28.4% | 2.15x | 0.338% / 1.078% |
| 2026-07-08 16:00 | 3.17x | Full-bodied bearish | Flat / fading | 0.425% / 0.480% / 0.425% | Position building in range | 73.3% | 4.4% | 22.3% | 4.07x | 0.087% / 0.756% |
| 2026-07-08 17:15 | 4.16x | Full-bodied bullish | Impulse / continuation | -0.023% / -0.109% / 0.884% | True breakout | 81.8% | 18.2% | 0.0% | 2.69x | 1.109% / 0.194% |
| 2026-07-08 18:15 | 4.00x | Full-bodied bullish | Reversal | -0.108% / -0.408% / -0.869% | Liquidity sweep / reversal | 72.9% | 27.1% | 0.0% | 1.47x | 0.131% / 1.023% |
| 2026-07-09 07:00 | 5.20x | Full-bodied bearish | Impulse / continuation | -0.453% / -0.390% / -0.430% | True breakout | 67.9% | 12.3% | 19.8% | 7.20x | 0.804% / 0.008% |
| 2026-07-09 07:15 | 5.64x | Bullish pin-bar / lower rejection | Flat / fading | 0.063% / -0.047% / 0.141% | Position building in range | 55.8% | 1.0% | 43.3% | 5.29x | 0.212% / 0.157% |
| 2026-07-09 09:00 | 2.59x | Small-body bearish | Reversal | 0.314% / 0.220% / 0.314% | Liquidity sweep / reversal | 24.5% | 38.8% | 36.7% | 1.52x | 0.047% / 0.330% |
| 2026-07-09 10:15 | 3.74x | Small-body bearish | Impulse / continuation | -0.417% / -0.110% / 0.110% | True breakout | 54.1% | 29.4% | 16.5% | 2.14x | 0.826% / 0.283% |
| 2026-07-09 10:30 | 3.64x | Bullish pin-bar / lower rejection | Reversal | 0.308% / 0.577% / 0.971% | Liquidity sweep / reversal | 43.8% | 13.2% | 43.0% | 2.64x | 0.158% / 1.106% |
| 2026-07-09 16:45 | 2.93x | Bullish pin-bar / lower rejection | Reversal | -0.063% / 0.094% / 0.203% | Liquidity sweep / reversal | 35.4% | 16.7% | 47.9% | 1.20x | 0.297% / 0.673% |
| 2026-07-09 19:15 | 2.68x | Full-bodied bearish | Flat / fading | -0.086% / -0.141% / -0.321% | Weak move without breakout | 82.4% | 0.0% | 17.6% | 1.16x | 0.360% / 0.118% |
| 2026-07-10 08:45 | 2.72x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.110% / 0.386% / 0.418% | True breakout | 25.0% | 30.6% | 44.4% | 1.51x | 1.009% / 0.213% |
| 2026-07-10 09:00 | 3.59x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.276% / 0.181% / -0.134% | False breakout | 46.7% | 53.3% | 0.0% | 1.19x | 0.898% / 0.323% |
| 2026-07-10 09:15 | 4.12x | Full-bodied bullish | Impulse -> reversal | -0.094% / 0.031% / -0.644% | False breakout | 64.8% | 24.1% | 11.1% | 2.05x | 0.620% / 0.840% |
| 2026-07-10 09:30 | 5.89x | Bearish pin-bar / upper rejection | Reversal | 0.126% / -0.314% / -0.259% | Liquidity sweep / reversal | 7.7% | 51.0% | 41.3% | 5.25x | 0.747% / 0.267% |
| 2026-07-10 11:00 | 2.91x | Small-body bearish | Impulse / continuation | -0.594% / -0.341% / -0.768% | True breakout | 56.1% | 8.8% | 35.1% | 1.14x | 1.371% / 0.158% |
| 2026-07-10 11:15 | 3.20x | Full-bodied bearish | Impulse / continuation | 0.255% / -0.183% / -0.223% | True breakout | 72.6% | 17.0% | 10.4% | 2.04x | 0.781% / 0.367% |
| 2026-07-10 12:00 | 2.83x | Bullish pin-bar / lower rejection | Reversal | -0.048% / 0.335% / 0.495% | Liquidity sweep / reversal | 2.6% | 0.0% | 97.4% | 1.19x | 0.647% / 0.088% |
| 2026-07-11 18:45 | 3.14x | Bearish pin-bar / upper rejection | Reversal | 0.024% / 0.275% / 0.194% | Liquidity sweep / reversal | 15.8% | 63.2% | 21.1% | 2.27x | 0.040% / 0.308% |
| 2026-07-12 10:00 | 6.92x | Full-bodied bullish | Flat / fading | -0.161% / -0.081% / -0.073% | Position building in range | 67.4% | 9.3% | 23.3% | 5.02x | -0.008% / 0.161% |
| 2026-07-12 13:45 | 3.31x | Full-bodied bullish | Flat / fading | -0.129% / -0.121% / -0.097% | Position building in range | 91.4% | 0.0% | 8.6% | 4.30x | -0.008% / 0.225% |
| 2026-07-13 07:00 | 2.64x | Full-bodied bearish | Reversal | 0.282% / 0.258% / 0.177% | Liquidity sweep / reversal | 61.9% | 33.3% | 4.8% | 4.00x | 0.016% / 0.387% |
| 2026-07-13 07:15 | 4.13x | Full-bodied bullish | Flat / fading | -0.024% / -0.056% / -0.088% | Position building in range | 72.0% | 26.0% | 2.0% | 3.83x | 0.056% / 0.225% |
| 2026-07-13 07:45 | 2.74x | Bullish pin-bar / lower rejection | Flat / fading | -0.048% / -0.032% / -0.088% | Weak move without breakout | 6.9% | 34.5% | 58.6% | 1.72x | 0.193% / 0.064% |
| 2026-07-13 09:00 | 5.33x | Full-bodied bearish | Reversal | 0.000% / 0.065% / 0.687% | Liquidity sweep / reversal | 68.7% | 31.3% | 0.0% | 2.24x | 0.162% / 0.808% |
| 2026-07-13 09:15 | 5.64x | Doji / upper rejection | Impulse / continuation | 0.065% / 0.008% / 1.204% | True breakout | 0.0% | 94.4% | 5.6% | 1.49x | 1.204% / 1.204% |
| 2026-07-13 09:45 | 4.19x | Bearish pin-bar / upper rejection | Reversal | 0.678% / 1.195% / 2.803% | Liquidity sweep / reversal | 12.0% | 46.0% | 42.0% | 1.90x | 0.048% / 2.819% |
| 2026-07-13 10:00 | 6.11x | Full-bodied bullish | Impulse / continuation | 0.513% / 1.388% / 1.508% | True breakout | 78.1% | 14.3% | 7.6% | 3.57x | 2.174% / 0.160% |
| 2026-07-13 10:15 | 8.84x | Full-bodied bullish | Impulse / continuation | 0.870% / 1.588% / 0.926% | True breakout | 77.4% | 0.0% | 22.6% | 2.33x | 1.652% / 0.008% |
| 2026-07-13 10:30 | 11.28x | Bearish pin-bar / upper rejection | Flat / fading | 0.712% / 0.119% / 0.443% | Weak move without breakout | 57.4% | 42.1% | 0.5% | 4.69x | 0.775% / 0.222% |
| 2026-07-13 10:45 | 2.62x | Full-bodied bullish | Flat / fading | -0.589% / -0.652% / -0.299% | Weak move without breakout | 75.0% | 1.7% | 23.3% | 2.35x | 0.063% / 0.896% |
| 2026-07-13 17:00 | 4.00x | Full-bodied bearish | Impulse / continuation | -0.016% / 0.286% / -0.740% | True breakout | 80.3% | 2.9% | 16.8% | 4.36x | 0.787% / 0.334% |
| 2026-07-13 17:15 | 3.28x | Bearish pin-bar / upper rejection | Reversal | 0.302% / -0.286% / -0.867% | Liquidity sweep / reversal | 8.2% | 59.0% | 32.8% | 1.23x | 1.082% / 0.350% |
| 2026-07-13 17:45 | 3.35x | Full-bodied bearish | Impulse / continuation | -0.439% / -0.582% / -0.391% | True breakout | 67.3% | 3.5% | 29.2% | 2.22x | 0.798% / 0.000% |
| 2026-07-13 18:00 | 2.62x | Full-bodied bearish | Flat / fading | -0.144% / -0.008% / 0.048% | Weak move without breakout | 90.2% | 0.0% | 9.8% | 1.07x | 0.361% / 0.144% |
| 2026-07-14 09:00 | 3.28x | Full-bodied bearish | Reversal | 0.096% / -0.072% / 0.519% | Liquidity sweep / reversal | 69.6% | 2.2% | 28.3% | 1.62x | 0.168% / 0.543% |
| 2026-07-14 10:15 | 3.08x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.199% / -0.437% / -0.167% | True breakout | 32.6% | 17.4% | 50.0% | 1.32x | 0.509% / 0.008% |
| 2026-07-15 07:00 | 4.79x | Bullish pin-bar / lower rejection | Reversal | -0.064% / 0.104% / -0.120% | Liquidity sweep / reversal | 27.9% | 23.3% | 48.8% | 3.34x | 0.249% / 0.185% |
| 2026-07-15 07:15 | 2.69x | Bullish pin-bar / lower rejection | Reversal | 0.169% / 0.056% / -0.032% | Liquidity sweep / reversal | 25.8% | 0.0% | 74.2% | 2.03x | 0.185% / 0.249% |
| 2026-07-15 07:30 | 3.28x | Full-bodied bullish | Reversal | -0.112% / -0.225% / -0.609% | Liquidity sweep / reversal | 65.6% | 31.2% | 3.1% | 1.94x | 0.000% / 0.962% |
| 2026-07-15 08:00 | 2.68x | Small-body bearish | Impulse / continuation | 0.024% / -0.386% / -0.394% | True breakout | 50.0% | 26.9% | 23.1% | 1.44x | 0.739% / 0.040% |
| 2026-07-15 08:30 | 6.40x | Bullish pin-bar / lower rejection | Flat / fading | 0.065% / -0.008% / 0.113% | Position building in range | 53.7% | 0.0% | 46.3% | 5.12x | 0.307% / 0.202% |
| 2026-07-15 08:45 | 3.07x | Bullish pin-bar / lower rejection | Reversal | -0.073% / 0.105% / -0.056% | Liquidity sweep / reversal | 12.0% | 8.0% | 80.0% | 2.07x | 0.137% / 0.258% |
| 2026-07-15 09:00 | 3.06x | Bullish pin-bar / lower rejection | Reversal | 0.178% / 0.121% / -0.032% | Liquidity sweep / reversal | 20.0% | 28.9% | 51.1% | 1.68x | 0.121% / 0.210% |
| 2026-07-15 10:15 | 3.20x | Full-bodied bearish | Impulse / continuation | 0.154% / -0.024% / -0.381% | True breakout | 90.7% | 5.6% | 3.7% | 1.58x | 0.486% / 0.373% |
| 2026-07-15 10:30 | 2.47x | Bearish pin-bar / upper rejection | Reversal | -0.178% / -0.178% / -0.882% | Liquidity sweep / reversal | 41.2% | 52.9% | 5.9% | 1.35x | 0.089% / 0.882% |
| 2026-07-15 11:15 | 2.62x | Full-bodied bearish | Impulse / continuation | -0.350% / -0.838% / -0.732% | True breakout | 61.6% | 20.5% | 17.8% | 1.88x | 0.919% / 0.220% |
| 2026-07-15 11:30 | 2.22x | Full-bodied bearish | Impulse / continuation | -0.490% / -0.392% / -0.465% | True breakout | 62.9% | 37.1% | 0.0% | 1.63x | 0.571% / 0.024% |
| 2026-07-15 11:45 | 2.87x | Full-bodied bearish | Flat / fading | 0.098% / 0.107% / 0.435% | Weak move without breakout | 85.7% | 4.3% | 10.0% | 1.52x | 0.082% / 0.451% |
| 2026-07-15 12:00 | 3.39x | Bearish pin-bar / upper rejection | Flat / fading | 0.008% / -0.074% / 0.246% | Position building in range | 20.0% | 66.2% | 13.8% | 1.31x | 0.352% / 0.123% |
| 2026-07-15 14:15 | 2.50x | Full-bodied bullish | Flat / fading | 0.016% / -0.260% / -0.536% | Weak move without breakout | 71.5% | 20.0% | 8.5% | 3.65x | 0.284% / 0.756% |
| 2026-07-16 07:00 | 5.79x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.140% / -0.074% / -0.330% | True breakout | 47.6% | 52.4% | 0.0% | 5.89x | 0.446% / 0.248% |
| 2026-07-16 07:15 | 2.91x | Small-body bullish | Reversal | -0.214% / -0.115% / -0.569% | Liquidity sweep / reversal | 40.5% | 28.6% | 31.0% | 1.76x | 0.107% / 0.709% |
| 2026-07-16 07:30 | 3.06x | Small-body bearish | Impulse / continuation | 0.099% / -0.256% / -0.091% | True breakout | 43.3% | 21.7% | 35.0% | 2.31x | 0.495% / 0.198% |
| 2026-07-16 08:00 | 2.64x | Full-bodied bearish | Impulse / continuation | -0.099% / 0.166% / -0.389% | True breakout | 77.4% | 0.0% | 22.6% | 2.20x | 0.406% / 0.240% |
| 2026-07-16 08:15 | 2.56x | Bullish pin-bar / lower rejection | Reversal | 0.265% / 0.124% / -0.108% | Liquidity sweep / reversal | 28.2% | 28.2% | 43.6% | 1.26x | 0.431% / 0.340% |
| 2026-07-16 09:15 | 2.70x | Small-body bullish | Reversal | -0.008% / -0.141% / -0.655% | Liquidity sweep / reversal | 38.6% | 31.6% | 29.8% | 1.40x | 0.207% / 1.236% |
| 2026-07-16 10:15 | 7.16x | Bullish pin-bar / lower rejection | Flat / fading | -0.084% / 0.184% / 0.643% | Position building in range | 45.4% | 14.4% | 40.2% | 3.61x | 0.384% / 0.651% |
| 2026-07-16 11:30 | 2.29x | Full-bodied bearish | Impulse / continuation | -0.242% / -1.267% / -0.633% | True breakout | 62.5% | 25.0% | 12.5% | 1.50x | 1.525% / 0.075% |
| 2026-07-16 12:00 | 2.65x | Full-bodied bearish | Flat / fading | 0.549% / 0.642% / 1.005% | Position building in range | 69.5% | 13.0% | 17.5% | 2.83x | 0.025% / 1.123% |
| 2026-07-16 23:45 | 2.67x | Full-bodied bearish | Reversal | 0.351% / 1.667% / 2.018% | Liquidity sweep / reversal | 68.4% | 5.3% | 26.2% | 4.02x | 0.386% / 2.677% |
| 2026-07-17 07:00 | 4.32x | Small-body bullish | Flat / fading | 0.285% / 0.345% / 0.388% | Weak move without breakout | 50.6% | 24.0% | 25.3% | 5.61x | 0.993% / 0.587% |
| 2026-07-17 07:15 | 3.13x | Bearish pin-bar / upper rejection | Flat / fading | 0.060% / 0.499% / 0.146% | Weak move without breakout | 21.0% | 44.2% | 34.8% | 2.44x | 0.706% / 0.336% |
| 2026-07-17 16:30 | 3.27x | Bullish pin-bar / lower rejection | Reversal | -0.095% / -0.286% / -0.572% | Liquidity sweep / reversal | 31.3% | 3.7% | 64.9% | 2.18x | 0.000% / 0.642% |
| 2026-07-17 17:45 | 2.59x | Full-bodied bearish | Impulse / continuation | 0.465% / -0.746% / 0.228% | True breakout | 69.6% | 8.9% | 21.4% | 1.84x | 0.974% / 0.597% |
| 2026-07-17 19:45 | 5.26x | Full-bodied bearish | Flat / fading | 0.188% / 0.305% / 0.538% | Position building in range | 61.0% | 4.4% | 34.5% | 3.15x | 0.153% / 0.664% |
| 2026-07-19 10:00 | 3.12x | Small-body bullish | Impulse / continuation | 0.369% / 0.193% / 0.185% | True breakout | 56.1% | 6.1% | 37.9% | 2.43x | 0.448% / 0.026% |
| 2026-07-19 10:15 | 3.46x | Full-bodied bullish | Flat / fading | -0.175% / -0.193% / -0.219% | Position building in range | 77.8% | 16.7% | 5.6% | 1.77x | 0.009% / 0.271% |
| 2026-07-19 16:30 | 5.85x | Full-bodied bullish | Flat / fading | 0.131% / 0.044% / 0.017% | Position building in range | 63.8% | 36.2% | 0.0% | 4.75x | 0.148% / 0.105% |
| 2026-07-19 18:00 | 2.93x | Bearish pin-bar / upper rejection | Flat / fading | 0.131% / 0.113% / -0.139% | Position building in range | 51.7% | 41.7% | 6.7% | 3.46x | 0.209% / 0.157% |
| 2026-07-20 07:00 | 20.27x | Small-body bearish | Impulse / continuation | -0.570% / -1.201% / -0.911% | True breakout | 41.1% | 38.3% | 20.6% | 7.52x | 1.358% / 0.000% |
| 2026-07-20 07:15 | 8.16x | Full-bodied bearish | Impulse / continuation | -0.635% / -0.696% / -0.185% | True breakout | 80.0% | 1.3% | 18.7% | 2.28x | 0.793% / 0.132% |
| 2026-07-20 07:30 | 6.25x | Full-bodied bearish | Flat / fading | -0.062% / 0.293% / 0.106% | Position building in range | 67.6% | 15.2% | 17.1% | 2.62x | 0.098% / 0.639% |
| 2026-07-20 09:45 | 4.44x | Full-bodied bullish | Impulse -> reversal | -0.132% / 0.758% / -1.269% | False breakout | 81.6% | 11.5% | 6.9% | 2.83x | 0.802% / 1.287% |
| 2026-07-20 10:00 | 3.18x | Bullish pin-bar / lower rejection | Reversal | 0.892% / 0.018% / -1.112% | Liquidity sweep / reversal | 12.8% | 38.5% | 48.7% | 1.61x | 1.642% / 0.936% |
| 2026-07-20 10:45 | 2.37x | Full-bodied bearish | Flat / fading | 0.027% / 0.536% / 0.616% | Weak move without breakout | 80.6% | 18.2% | 1.2% | 1.97x | 0.509% / 0.920% |
| 2026-07-20 15:45 | 6.96x | Full-bodied bullish | Impulse / continuation | 1.261% / 1.355% / 0.486% | True breakout | 75.8% | 21.7% | 2.4% | 2.64x | 1.994% / 0.136% |
| 2026-07-20 16:00 | 3.77x | Full-bodied bullish | Reversal | 0.093% / -0.858% / -1.498% | Liquidity sweep / reversal | 64.5% | 29.0% | 6.5% | 2.62x | 0.724% / 1.548% |
| 2026-07-20 16:15 | 2.71x | Bearish pin-bar / upper rejection | Reversal | -0.950% / -0.858% / -0.933% | Liquidity sweep / reversal | 5.2% | 56.0% | 38.8% | 1.34x | 0.387% / 1.639% |
| 2026-07-20 16:30 | 2.86x | Small-body bearish | Flat / fading | 0.093% / -0.645% / 0.059% | Weak move without breakout | 59.7% | 23.6% | 16.8% | 1.83x | 0.696% / 0.789% |
| 2026-07-21 07:00 | 3.50x | Bullish pin-bar / lower rejection | Reversal | -0.714% / -0.872% / -0.548% | Liquidity sweep / reversal | 30.2% | 23.6% | 46.2% | 5.18x | 0.208% / 1.328% |
| 2026-07-21 07:15 | 3.09x | Full-bodied bearish | Impulse / continuation | -0.159% / -0.602% / 0.125% | True breakout | 69.4% | 20.2% | 10.5% | 2.21x | 0.619% / 0.535% |
| 2026-07-21 09:00 | 4.05x | Small-body bullish | Reversal | 0.239% / 0.239% / -0.880% | Liquidity sweep / reversal | 55.1% | 23.4% | 21.5% | 2.16x | 0.674% / 1.283% |
| 2026-07-21 09:15 | 3.80x | Bearish pin-bar / upper rejection | Reversal | 0.000% / -0.254% / -1.616% | Liquidity sweep / reversal | 34.1% | 50.6% | 15.3% | 1.04x | 0.435% / 1.649% |
| 2026-07-21 16:00 | 2.62x | Full-bodied bullish | Impulse / continuation | 0.491% / 0.638% / 1.611% | True breakout | 63.7% | 35.1% | 1.2% | 1.67x | 1.978% / 0.540% |
| 2026-07-22 07:00 | 5.12x | Bullish pin-bar / lower rejection | Flat / fading | -0.347% / -0.048% / -0.274% | Position building in range | 43.1% | 2.4% | 54.5% | 4.25x | 0.468% / 0.178% |
| 2026-07-22 08:45 | 3.16x | Full-bodied bearish | Impulse / continuation | -0.520% / -0.577% / -0.187% | True breakout | 75.3% | 1.0% | 23.7% | 2.51x | 1.000% / 0.081% |
| 2026-07-22 09:00 | 5.43x | Bullish pin-bar / lower rejection | Reversal | -0.057% / 0.278% / 0.662% | Liquidity sweep / reversal | 48.1% | 7.5% | 44.4% | 3.04x | 0.302% / 0.760% |
| 2026-07-22 12:00 | 8.58x | Full-bodied bullish | Impulse / continuation | -0.280% / -0.312% / 1.008% | True breakout | 76.6% | 23.4% | 0.0% | 4.30x | 1.496% / 0.696% |
| 2026-07-22 12:45 | 2.87x | Full-bodied bullish | Flat / fading | -0.048% / 0.040% / -0.024% | Weak move without breakout | 90.0% | 5.3% | 4.7% | 2.21x | 0.435% / 0.325% |
| 2026-07-22 13:00 | 2.89x | Bearish pin-bar / upper rejection | Reversal | 0.087% / 0.055% / 0.317% | Liquidity sweep / reversal | 6.3% | 57.3% | 36.5% | 1.02x | 0.190% / 0.515% |
| 2026-07-23 07:00 | 4.50x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.000% / -0.252% / 0.205% | True breakout | 39.6% | 52.7% | 7.7% | 3.53x | 0.520% / 0.205% |
| 2026-07-23 07:30 | 5.59x | Bullish pin-bar / lower rejection | Reversal | -0.008% / 0.458% / 0.332% | Liquidity sweep / reversal | 48.5% | 0.0% | 51.5% | 2.19x | 0.071% / 0.790% |
| 2026-07-23 08:45 | 2.96x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.181% / 0.645% / 0.039% | True breakout | 32.7% | 20.4% | 46.9% | 1.22x | 0.951% / 0.031% |
| 2026-07-23 09:15 | 3.60x | Small-body bullish | Reversal | 0.078% / -0.602% / -0.898% | Liquidity sweep / reversal | 46.3% | 32.2% | 21.5% | 2.85x | 0.227% / 1.180% |
| 2026-07-23 10:00 | 3.48x | Small-body bearish | Impulse / continuation | 0.103% / -0.592% / -0.647% | True breakout | 51.5% | 24.7% | 23.7% | 1.67x | 1.144% / 0.213% |
| 2026-07-23 10:30 | 2.77x | Full-bodied bearish | Impulse / continuation | -0.222% / -0.056% / -1.214% | True breakout | 78.1% | 0.0% | 21.9% | 1.81x | 1.484% / 0.230% |
| 2026-07-23 11:15 | 2.95x | Full-bodied bearish | Flat / fading | -0.056% / 0.112% / 0.498% | Position building in range | 77.2% | 0.0% | 22.8% | 2.60x | 0.193% / 0.610% |
| 2026-07-24 07:15 | 2.89x | Small-body bearish | Reversal | 0.024% / 0.170% / 0.428% | Liquidity sweep / reversal | 52.7% | 19.8% | 27.5% | 3.08x | 0.057% / 0.654% |
| 2026-07-24 09:30 | 2.66x | Bullish pin-bar / lower rejection | Reversal | -0.194% / -0.653% / -0.790% | Liquidity sweep / reversal | 2.2% | 28.3% | 69.6% | 1.23x | 0.169% / 1.234% |
| 2026-07-24 10:00 | 5.24x | Full-bodied bearish | Impulse / continuation | -0.130% / -0.138% / -0.836% | True breakout | 81.9% | 1.4% | 16.7% | 1.88x | 1.031% / 0.000% |
| 2026-07-24 10:15 | 5.43x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.008% / -0.228% / -0.845% | True breakout | 20.8% | 1.4% | 77.8% | 1.69x | 0.935% / 0.041% |
| 2026-07-24 11:30 | 3.52x | Full-bodied bullish | Flat / fading | -0.495% / -0.625% / -0.568% | Position building in range | 75.5% | 22.6% | 1.9% | 3.49x | 0.081% / 0.990% |
| 2026-07-24 13:15 | 2.45x | Small-body bullish | Impulse / continuation | 1.017% / 1.302% / 0.521% | True breakout | 49.4% | 22.5% | 28.1% | 2.54x | 3.370% / 0.000% |
| 2026-07-24 13:30 | 17.08x | Bearish pin-bar / upper rejection | Reversal | 0.282% / -0.226% / -1.080% | Liquidity sweep / reversal | 30.2% | 69.8% | 0.0% | 5.83x | 0.757% / 1.217% |
| 2026-07-26 10:00 | 16.93x | Full-bodied bearish | Flat / fading | 0.077% / 0.604% / 0.306% | Position building in range | 75.4% | 1.5% | 23.1% | 15.08x | 0.230% / 0.650% |
| 2026-07-26 10:15 | 5.92x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.527% / 0.130% / 0.107% | True breakout | 15.2% | 39.4% | 45.5% | 2.48x | 0.573% / 0.191% |
| 2026-07-26 10:30 | 2.74x | Full-bodied bullish | Flat / fading | -0.395% / -0.297% / -0.517% | Weak move without breakout | 98.6% | 1.4% | 0.0% | 2.33x | 0.046% / 0.715% |
| 2026-07-27 07:00 | 13.98x | Bullish pin-bar / lower rejection | Reversal | 0.537% / 0.683% / 0.936% | Liquidity sweep / reversal | 24.7% | 0.6% | 74.7% | 8.01x | 0.038% / 1.136% |
| 2026-07-27 07:15 | 5.81x | Full-bodied bullish | Impulse / continuation | 0.145% / 0.099% / 0.366% | True breakout | 63.6% | 31.8% | 4.5% | 3.37x | 0.611% / 0.076% |
| 2026-07-27 07:30 | 3.56x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.046% / 0.252% / 0.434% | True breakout | 32.2% | 50.8% | 16.9% | 1.54x | 0.564% / 0.145% |
| 2026-07-27 07:45 | 5.36x | Bearish pin-bar / upper rejection | Reversal | 0.297% / 0.267% / 0.244% | Liquidity sweep / reversal | 8.1% | 74.3% | 17.6% | 1.82x | 0.031% / 0.610% |
| 2026-07-27 09:00 | 3.81x | Bullish pin-bar / lower rejection | Flat / fading | -0.450% / -0.213% / 0.030% | Weak move without breakout | 26.6% | 18.1% | 55.3% | 1.82x | 0.709% / 0.213% |
| 2026-07-27 09:15 | 3.80x | Small-body bearish | Reversal | 0.237% / 0.176% / 0.329% | Liquidity sweep / reversal | 58.3% | 8.7% | 33.0% | 1.79x | 0.084% / 0.666% |
| 2026-07-27 10:45 | 3.74x | Full-bodied bullish | Flat / fading | 0.114% / -0.061% / -0.318% | Weak move without breakout | 91.0% | 0.0% | 9.0% | 0.98x | 0.288% / 0.432% |
| 2026-07-27 13:15 | 2.09x | Full-bodied bullish | Impulse / continuation | 0.227% / 0.250% / 0.508% | True breakout | 84.0% | 9.3% | 6.7% | 1.24x | 0.781% / 0.045% |
| 2026-07-28 07:00 | 3.68x | Full-bodied bullish | Impulse / continuation | 0.219% / 0.431% / 0.212% | True breakout | 84.6% | 2.6% | 12.8% | 1.89x | 0.461% / 0.000% |
| 2026-07-28 07:15 | 3.83x | Full-bodied bullish | Flat / fading | 0.211% / 0.166% / -0.098% | Weak move without breakout | 69.0% | 31.0% | 0.0% | 1.92x | 0.241% / 0.204% |
| 2026-07-28 07:30 | 2.59x | Full-bodied bullish | Reversal | -0.045% / -0.218% / -0.346% | Liquidity sweep / reversal | 74.4% | 10.3% | 15.4% | 1.65x | 0.015% / 0.414% |
| 2026-07-28 09:15 | 3.19x | Full-bodied bullish | Reversal | -0.255% / -0.413% / -1.231% | Liquidity sweep / reversal | 63.5% | 33.3% | 3.1% | 3.75x | 0.053% / 1.419% |
| 2026-07-28 09:45 | 2.54x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.369% / -0.822% / -1.546% | True breakout | 50.0% | 2.4% | 47.6% | 1.23x | 1.757% / 0.008% |
| 2026-07-28 10:00 | 5.60x | Full-bodied bearish | Impulse / continuation | -0.454% / -0.863% / -1.567% | True breakout | 62.0% | 1.3% | 36.7% | 2.23x | 2.058% / 0.166% |
| 2026-07-28 10:15 | 2.65x | Small-body bearish | Impulse / continuation | -0.411% / -0.730% / -0.920% | True breakout | 55.1% | 21.5% | 23.4% | 2.69x | 1.612% / 0.068% |
| 2026-07-28 10:30 | 2.70x | Full-bodied bearish | Impulse / continuation | -0.321% / -0.710% / -0.176% | True breakout | 61.0% | 20.8% | 18.2% | 1.63x | 1.206% / 0.168% |
| 2026-07-28 10:45 | 3.86x | Small-body bearish | Impulse / continuation | -0.391% / -0.191% / -0.176% | True breakout | 44.6% | 25.0% | 30.4% | 1.84x | 0.888% / 0.291% |
| 2026-07-28 11:00 | 3.52x | Bullish pin-bar / lower rejection | Reversal | 0.200% / 0.538% / 0.315% | Liquidity sweep / reversal | 40.0% | 10.0% | 50.0% | 2.43x | 0.292% / 0.684% |
| 2026-07-28 16:45 | 2.57x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.183% / 0.061% / 0.382% | False breakout | 45.1% | 52.0% | 2.9% | 2.04x | 0.520% / 0.642% |
| 2026-07-29 07:15 | 2.67x | Small-body bullish | Flat / fading | -0.151% / -0.144% / -0.197% | Position building in range | 58.9% | 30.4% | 10.7% | 2.75x | 0.008% / 0.295% |
| 2026-07-29 09:30 | 3.04x | Bearish pin-bar / upper rejection | Reversal | 0.106% / -0.068% / 0.129% | Liquidity sweep / reversal | 31.4% | 54.9% | 13.7% | 1.68x | 0.121% / 0.296% |
| 2026-07-29 09:45 | 2.95x | Bearish pin-bar / upper rejection | Reversal | -0.174% / 0.023% / 0.522% | Liquidity sweep / reversal | 37.1% | 42.9% | 20.0% | 1.07x | 0.803% / 0.227% |
| 2026-07-29 10:00 | 2.50x | Bearish pin-bar / upper rejection | Reversal | 0.197% / 0.197% / 0.948% | Liquidity sweep / reversal | 40.0% | 47.3% | 12.7% | 1.67x | 0.015% / 1.259% |
| 2026-07-29 10:45 | 8.04x | Full-bodied bullish | Impulse / continuation | 0.249% / 0.226% / -0.023% | True breakout | 60.8% | 36.3% | 2.9% | 2.83x | 0.557% / 0.105% |
| 2026-07-29 11:00 | 3.44x | Bearish pin-bar / upper rejection | Reversal | -0.023% / -0.286% / -0.203% | Liquidity sweep / reversal | 42.3% | 57.7% | 0.0% | 1.80x | 0.158% / 0.353% |
| 2026-07-29 11:15 | 2.59x | Bullish pin-bar / lower rejection | Flat / fading | -0.263% / -0.248% / -0.150% | Weak move without breakout | 6.1% | 42.9% | 51.0% | 1.16x | 0.331% / 0.023% |
| 2026-07-29 15:30 | 2.09x | Bullish pin-bar / lower rejection | Reversal | -0.277% / -0.239% / -0.254% | Liquidity sweep / reversal | 30.0% | 26.7% | 43.3% | 0.69x | 0.007% / 0.404% |
| 2026-07-29 18:15 | 3.09x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.090% / 0.015% / -0.037% | True breakout | 46.2% | 51.9% | 1.9% | 1.64x | 0.463% / 0.157% |
| 2026-07-29 19:00 | 3.57x | Bearish pin-bar / upper rejection | Reversal | -0.283% / -0.223% / -0.194% | Liquidity sweep / reversal | 48.5% | 43.9% | 7.6% | 2.14x | 0.216% / 0.380% |
| 2026-07-30 08:15 | 2.74x | Full-bodied bullish | Flat / fading | -0.141% / -0.037% / -0.141% | Weak move without breakout | 98.1% | 0.0% | 1.9% | 2.18x | 0.082% / 0.319% |
| 2026-07-30 09:30 | 3.83x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.141% / 0.156% / 0.734% | True breakout | 47.3% | 40.0% | 12.7% | 1.87x | 0.763% / 0.104% |
| 2026-07-30 10:30 | 6.09x | Full-bodied bullish | Reversal | -0.368% / -0.824% / -0.677% | Liquidity sweep / reversal | 84.9% | 5.5% | 9.6% | 1.95x | 0.022% / 1.221% |
| 2026-07-30 11:00 | 4.27x | Bullish pin-bar / lower rejection | Flat / fading | -0.074% / 0.148% / -0.237% | Position building in range | 51.2% | 4.1% | 44.6% | 2.90x | 0.349% / 0.304% |
| 2026-07-30 12:30 | 3.32x | Bullish pin-bar / lower rejection | Flat / fading | 0.142% / -0.015% / 0.405% | Position building in range | 49.4% | 5.8% | 44.8% | 2.97x | 0.165% / 0.494% |
| 2026-07-30 17:45 | 3.29x | Bullish pin-bar / lower rejection | Reversal | 0.082% / -0.270% / -0.652% | Liquidity sweep / reversal | 12.6% | 28.7% | 58.6% | 1.74x | 0.240% / 0.899% |
| 2026-07-31 07:00 | 4.61x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.090% / -0.030% / -0.421% | True breakout | 48.3% | 2.6% | 49.0% | 4.74x | 0.436% / 0.488% |
| 2026-07-31 07:15 | 3.82x | Bearish pin-bar / upper rejection | Reversal | -0.120% / -0.495% / -0.638% | Liquidity sweep / reversal | 13.0% | 50.0% | 37.0% | 2.38x | 0.090% / 0.901% |
| 2026-08-03 07:00 | 5.57x | Full-bodied bullish | Impulse / continuation | 0.231% / 0.418% / 0.164% | True breakout | 66.7% | 33.3% | 0.0% | 4.06x | 0.537% / 0.090% |
| 2026-08-03 07:15 | 6.19x | Bearish pin-bar / upper rejection | Flat / fading | 0.186% / 0.089% / 0.260% | Weak move without breakout | 42.1% | 43.4% | 14.5% | 3.72x | 0.394% / 0.074% |
| 2026-08-03 07:30 | 3.70x | Small-body bullish | Reversal | -0.097% / -0.253% / 0.111% | Liquidity sweep / reversal | 53.3% | 22.2% | 24.4% | 1.78x | 0.208% / 0.253% |
| 2026-08-03 07:45 | 3.29x | Bearish pin-bar / upper rejection | Reversal | -0.156% / 0.171% / 0.186% | Liquidity sweep / reversal | 42.4% | 45.5% | 12.1% | 1.19x | 0.156% / 0.305% |
| 2026-08-03 09:00 | 2.64x | Bearish pin-bar / upper rejection | Reversal | -0.126% / -0.163% / 0.356% | Liquidity sweep / reversal | 57.6% | 42.4% | 0.0% | 0.93x | 0.393% / 0.289% |
| 2026-08-03 10:00 | 3.35x | Full-bodied bullish | Impulse / continuation | 0.126% / 0.709% / 0.532% | True breakout | 68.8% | 6.5% | 24.7% | 2.03x | 0.923% / 0.000% |
| 2026-08-03 10:30 | 2.97x | Full-bodied bullish | Flat / fading | -0.161% / -0.176% / 0.117% | Weak move without breakout | 81.4% | 7.2% | 11.3% | 2.31x | 0.213% / 0.257% |
| 2026-08-04 07:00 | 4.78x | Small-body bullish | Impulse / continuation | 0.674% / 0.747% / 0.395% | True breakout | 51.1% | 35.6% | 13.3% | 1.86x | 0.930% / 0.022% |
| 2026-08-04 07:15 | 11.88x | Full-bodied bullish | Flat / fading | 0.073% / -0.080% / -0.480% | Position building in range | 70.8% | 26.9% | 2.3% | 5.20x | 0.255% / 0.538% |
| 2026-08-04 08:45 | 2.84x | Full-bodied bearish | Reversal | 0.132% / 0.425% / 0.103% | Liquidity sweep / reversal | 60.5% | 0.0% | 39.5% | 2.28x | 0.022% / 0.469% |
| 2026-08-04 18:15 | 3.36x | Small-body bullish | Flat / fading | -0.022% / 0.309% / 0.243% | Weak move without breakout | 60.0% | 32.3% | 7.7% | 1.42x | 0.316% / 0.074% |
| 2026-08-05 07:00 | 2.91x | Bullish pin-bar / lower rejection | Reversal | 0.029% / 0.147% / 0.360% | Liquidity sweep / reversal | 48.8% | 7.0% | 44.2% | 2.21x | 0.081% / 0.462% |
| 2026-08-05 09:00 | 2.53x | Full-bodied bullish | Impulse / continuation | -0.088% / 0.146% / 0.233% | True breakout | 77.3% | 18.2% | 4.5% | 1.79x | 0.241% / 0.131% |
| 2026-08-05 09:15 | 2.85x | Bearish pin-bar / upper rejection | Reversal | 0.234% / 0.197% / 0.519% | Liquidity sweep / reversal | 23.7% | 60.5% | 15.8% | 1.40x | 0.022% / 0.526% |
| 2026-08-05 10:00 | 2.80x | Bullish pin-bar / lower rejection | Impulse -> reversal | 0.197% / 0.015% / -0.189% | False breakout | 41.5% | 2.4% | 56.1% | 1.28x | 0.277% / 0.379% |
| 2026-08-05 10:15 | 4.98x | Full-bodied bullish | Reversal | -0.182% / -0.240% / -0.429% | Liquidity sweep / reversal | 96.6% | 3.4% | 0.0% | 0.86x | 0.080% / 0.574% |
| 2026-08-05 10:30 | 2.87x | Small-body bearish | Impulse / continuation | -0.058% / -0.204% / -0.480% | True breakout | 53.2% | 23.4% | 23.4% | 1.35x | 0.619% / 0.146% |
| 2026-08-05 19:00 | 3.41x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.267% / 0.231% / 0.368% | True breakout | 11.8% | 70.6% | 17.6% | 1.47x | 0.483% / 0.029% |
| 2026-08-06 07:00 | 8.59x | Full-bodied bullish | Flat / fading | -0.142% / -0.531% / -0.545% | Position building in range | 91.5% | 8.5% | 0.0% | 7.97x | 0.064% / 0.786% |
| 2026-08-06 07:15 | 2.67x | Small-body bearish | Impulse / continuation | -0.390% / -0.575% / -0.646% | True breakout | 50.0% | 22.5% | 27.5% | 1.28x | 0.752% / 0.000% |
| 2026-08-06 07:30 | 3.15x | Full-bodied bearish | Impulse / continuation | -0.185% / -0.014% / -0.100% | True breakout | 77.1% | 1.4% | 21.4% | 2.08x | 0.363% / 0.171% |
| 2026-08-06 11:45 | 2.73x | Full-bodied bearish | Impulse / continuation | 0.259% / 0.086% / -0.014% | True breakout | 76.3% | 11.9% | 11.9% | 2.45x | 0.597% / 0.359% |
| 2026-08-07 07:00 | 3.28x | Small-body bearish | Impulse / continuation | -0.314% / 0.000% / 0.242% | True breakout | 56.5% | 8.1% | 35.5% | 2.90x | 0.385% / 0.371% |
| 2026-08-07 08:00 | 3.19x | Full-bodied bullish | Reversal | -0.199% / -0.370% / -0.569% | Liquidity sweep / reversal | 64.7% | 35.3% | 0.0% | 2.06x | 0.128% / 0.811% |
| 2026-08-07 16:45 | 2.14x | Small-body bullish | Impulse / continuation | 0.229% / 0.143% / 0.021% | True breakout | 34.7% | 30.6% | 34.7% | 2.02x | 0.314% / 0.093% |
| 2026-08-07 23:30 | 3.66x | Full-bodied bullish | Impulse -> reversal | 0.093% / -1.075% / -1.239% | False breakout | 85.2% | 0.0% | 14.8% | 1.44x | 0.235% / 1.553% |
| 2026-08-07 23:45 | 2.58x | Bearish pin-bar / upper rejection | Reversal | -1.167% / -1.245% / -1.366% | Liquidity sweep / reversal | 31.1% | 44.4% | 24.4% | 2.31x | -1.096% / 1.644% |
| 2026-08-08 10:00 | 2.68x | Bullish pin-bar / lower rejection | Flat / fading | -0.086% / -0.122% / -0.072% | Position building in range | 11.7% | 15.6% | 72.7% | 2.45x | 0.209% / 0.000% |
| 2026-08-08 17:00 | 13.58x | Full-bodied bullish | Impulse / continuation | -0.172% / 0.086% / -0.029% | True breakout | 89.3% | 0.0% | 10.7% | 11.54x | 0.294% / 0.301% |
| 2026-08-08 17:15 | 4.20x | Bullish pin-bar / lower rejection | Reversal | 0.258% / 0.237% / 0.151% | Liquidity sweep / reversal | 46.2% | 7.7% | 46.2% | 2.44x | 0.000% / 0.466% |
| 2026-08-08 17:30 | 4.56x | Bearish pin-bar / upper rejection | Reversal | -0.021% / -0.114% / -0.258% | Liquidity sweep / reversal | 49.2% | 44.6% | 6.2% | 3.50x | 0.007% / 0.265% |
| 2026-08-09 16:00 | 6.53x | Bearish pin-bar / upper rejection | Flat / fading | -0.036% / 0.014% / 0.007% | Position building in range | 18.2% | 66.7% | 15.2% | 6.08x | 0.014% / 0.043% |
| 2026-08-09 18:15 | 4.62x | Bearish pin-bar / upper rejection | Reversal | -0.007% / 0.043% / 0.079% | Liquidity sweep / reversal | 20.0% | 50.0% | 30.0% | 1.27x | 0.122% / 0.258% |
| 2026-08-10 07:00 | 10.01x | Bullish pin-bar / lower rejection | Flat / fading | -0.036% / -0.050% / -0.129% | Weak move without breakout | 41.5% | 5.7% | 52.8% | 5.34x | 0.258% / 0.079% |
| 2026-08-10 07:15 | 3.82x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.014% / -0.014% / -0.057% | True breakout | 20.8% | 45.8% | 33.3% | 1.79x | 0.222% / 0.093% |
| 2026-08-10 07:30 | 4.92x | Bearish pin-bar / upper rejection | Impulse -> reversal | 0.000% / -0.079% / 0.036% | False breakout | 7.7% | 50.0% | 42.3% | 2.03x | 0.208% / 0.036% |
| 2026-08-10 08:00 | 2.99x | Bullish pin-bar / lower rejection | Reversal | 0.036% / 0.115% / 0.057% | Liquidity sweep / reversal | 37.9% | 0.0% | 62.1% | 2.05x | 0.151% / 0.115% |
| 2026-08-10 09:00 | 2.94x | Bullish pin-bar / lower rejection | Reversal | -0.057% / 0.115% / 0.179% | Liquidity sweep / reversal | 23.1% | 26.9% | 50.0% | 1.29x | 0.258% / 0.129% |
| 2026-08-10 09:45 | 2.67x | Full-bodied bullish | Reversal | -0.057% / -0.136% / -0.293% | Liquidity sweep / reversal | 63.0% | 7.4% | 29.6% | 1.12x | 0.057% / 0.336% |
| 2026-08-10 11:00 | 3.73x | Full-bodied bearish | Flat / fading | 0.180% / -0.065% / 0.137% | Weak move without breakout | 82.9% | 5.7% | 11.4% | 2.63x | 0.202% / 0.194% |
| 2026-08-10 14:30 | 2.19x | Full-bodied bearish | Flat / fading | -0.043% / 0.239% / 0.224% | Weak move without breakout | 90.2% | 0.0% | 9.8% | 1.37x | 0.080% / 0.398% |
| 2026-08-10 15:00 | 2.01x | Full-bodied bullish | Flat / fading | 0.000% / -0.014% / 0.173% | Weak move without breakout | 62.9% | 35.5% | 1.6% | 2.27x | 0.231% / 0.187% |
| 2026-08-11 07:00 | 3.02x | Doji / lower rejection | Impulse / continuation | 0.158% / 0.301% / 0.430% | True breakout | 0.0% | 32.4% | 67.6% | 3.14x | 0.696% / 0.696% |
| 2026-08-11 07:15 | 2.65x | Full-bodied bullish | Impulse / continuation | 0.143% / 0.415% / 0.093% | True breakout | 61.1% | 22.2% | 16.7% | 2.61x | 0.537% / 0.000% |
| 2026-08-11 07:30 | 6.24x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.272% / 0.129% / -0.007% | True breakout | 37.7% | 62.3% | 0.0% | 3.37x | 0.393% / 0.129% |
| 2026-08-11 10:00 | 5.54x | Full-bodied bullish | Flat / fading | 0.142% / 0.164% / -0.085% | Weak move without breakout | 86.0% | 11.6% | 2.3% | 2.75x | 0.284% / 0.227% |
| 2026-08-11 10:15 | 4.63x | Small-body bullish | Reversal | 0.021% / -0.248% / 0.014% | Liquidity sweep / reversal | 37.0% | 35.2% | 27.8% | 1.49x | 0.142% / 0.369% |
| 2026-08-11 13:15 | 2.41x | Full-bodied bullish | Flat / fading | -0.092% / -0.014% / -0.085% | Weak move without breakout | 60.2% | 35.2% | 4.5% | 2.25x | 0.304% / 0.304% |
| 2026-08-11 13:30 | 2.67x | Bearish pin-bar / upper rejection | Flat / fading | 0.078% / -0.120% / 0.035% | Weak move without breakout | 16.9% | 55.8% | 27.3% | 1.82x | 0.212% / 0.106% |
| 2026-08-12 07:00 | 2.82x | Full-bodied bullish | Impulse / continuation | -0.035% / 0.070% / 0.387% | True breakout | 62.5% | 10.4% | 27.1% | 2.37x | 0.458% / 0.106% |
| 2026-08-12 10:00 | 2.64x | Full-bodied bearish | Impulse / continuation | -0.289% / -0.183% / -0.458% | True breakout | 89.7% | 3.4% | 6.9% | 1.99x | 0.557% / 0.000% |
| 2026-08-12 10:15 | 3.50x | Bullish pin-bar / lower rejection | Flat / fading | 0.106% / 0.000% / -0.064% | Weak move without breakout | 59.4% | 0.0% | 40.6% | 2.17x | 0.268% / 0.240% |
| 2026-08-12 10:30 | 3.32x | Bullish pin-bar / lower rejection | Reversal | -0.106% / -0.275% / -0.381% | Liquidity sweep / reversal | 20.8% | 26.4% | 52.8% | 1.96x | 0.071% / 0.409% |
| 2026-08-12 14:30 | 2.34x | Full-bodied bearish | Impulse / continuation | -0.142% / -0.078% / -0.007% | True breakout | 75.9% | 13.8% | 10.3% | 2.89x | 0.405% / 0.263% |
| 2026-08-12 23:00 | 6.00x | Full-bodied bearish | Flat / fading | -0.086% / 0.065% / 0.115% | Position building in range | 67.6% | 2.8% | 29.6% | 4.19x | 0.101% / 0.115% |
| 2026-08-13 07:00 | 6.65x | Full-bodied bearish | Flat / fading | -0.015% / 0.029% / 0.022% | Position building in range | 69.2% | 9.4% | 21.4% | 6.10x | 0.218% / 0.181% |
| 2026-08-13 10:00 | 2.67x | Bearish pin-bar / upper rejection | Reversal | -0.388% / -0.416% / -0.675% | Liquidity sweep / reversal | 4.7% | 65.1% | 30.2% | 1.03x | 0.022% / 0.998% |
| 2026-08-13 10:45 | 3.73x | Full-bodied bearish | Flat / fading | 0.022% / 0.029% / -0.094% | Weak move without breakout | 77.6% | 4.1% | 18.4% | 1.21x | 0.304% / 0.311% |
| 2026-08-13 12:15 | 3.45x | Bullish pin-bar / lower rejection | Flat / fading | -0.117% / -0.219% / -0.015% | Position building in range | 46.8% | 0.0% | 53.2% | 2.37x | 0.474% / 0.153% |
| 2026-08-13 16:30 | 3.47x | Small-body bearish | Flat / fading | -0.327% / -0.379% / -0.512% | Weak move without breakout | 45.6% | 16.7% | 37.7% | 2.13x | 0.616% / 0.148% |
| 2026-08-13 22:30 | 2.95x | Full-bodied bearish | Impulse / continuation | -0.015% / 0.000% / -0.346% | True breakout | 80.7% | 5.3% | 14.0% | 3.19x | 0.549% / 0.113% |
| 2026-08-14 07:00 | 6.33x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.203% / 0.655% / 0.662% | True breakout | 32.2% | 48.6% | 19.2% | 4.91x | 1.053% / 0.293% |
| 2026-08-14 10:00 | 2.77x | Full-bodied bullish | Flat / fading | 0.201% / -0.342% / 0.082% | Weak move without breakout | 84.8% | 15.2% | 0.0% | 2.06x | 0.305% / 0.401% |
| 2026-08-14 11:15 | 2.76x | Full-bodied bearish | Impulse / continuation | 0.234% / -0.332% / -1.299% | True breakout | 85.6% | 3.5% | 10.9% | 4.46x | 1.427% / 0.476% |
| 2026-08-14 11:45 | 3.00x | Full-bodied bearish | Impulse / continuation | -0.083% / -0.970% / -0.924% | True breakout | 61.0% | 10.6% | 28.5% | 1.71x | 1.098% / 0.167% |
| 2026-08-14 12:15 | 3.24x | Full-bodied bearish | Impulse / continuation | 0.367% / 0.046% / -0.903% | True breakout | 87.3% | 0.0% | 12.7% | 1.73x | 1.446% / 0.398% |
| 2026-08-14 13:00 | 3.00x | Full-bodied bearish | Impulse / continuation | -0.170% / 0.100% / -0.709% | True breakout | 81.6% | 0.0% | 18.4% | 1.45x | 2.096% / 0.324% |
| 2026-08-14 13:45 | 3.28x | Full-bodied bearish | Flat / fading | 0.476% / 0.624% / -0.039% | Weak move without breakout | 80.1% | 0.0% | 19.9% | 2.21x | 0.928% / 0.951% |
| 2026-08-14 14:00 | 3.57x | Bullish pin-bar / lower rejection | Reversal | 0.147% / -0.396% / 0.210% | Liquidity sweep / reversal | 29.0% | 10.0% | 61.0% | 1.90x | 0.473% / 0.761% |
| 2026-08-14 16:15 | 2.40x | Bullish pin-bar / lower rejection | Reversal | 0.047% / 0.031% / 0.683% | Liquidity sweep / reversal | 34.5% | 22.3% | 43.2% | 1.17x | 0.165% / 0.770% |
| 2026-08-17 07:00 | 23.06x | Full-bodied bearish | Flat / fading | 0.056% / 0.008% / 0.063% | Weak move without breakout | 82.6% | 3.6% | 13.8% | 7.96x | 0.270% / 0.500% |
| 2026-08-17 07:15 | 5.30x | Bearish pin-bar / upper rejection | Reversal | -0.048% / 0.008% / -0.531% | Liquidity sweep / reversal | 7.2% | 57.7% | 35.1% | 2.61x | 0.309% / 0.928% |
| 2026-08-17 08:15 | 4.95x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.032% / 0.072% / -0.630% | True breakout | 55.9% | 1.7% | 42.4% | 2.57x | 0.813% / 0.678% |
| 2026-08-17 09:00 | 2.93x | Bullish pin-bar / lower rejection | Reversal | -0.495% / 0.295% / 0.711% | Liquidity sweep / reversal | 26.0% | 15.6% | 58.3% | 1.83x | 0.679% / 0.814% |
| 2026-08-17 09:15 | 7.02x | Bearish pin-bar / upper rejection | Reversal | 0.794% / 0.818% / 0.899% | Liquidity sweep / reversal | 29.4% | 58.3% | 12.3% | 3.24x | 0.040% / 1.252% |
| 2026-08-17 17:00 | 2.58x | Full-bodied bullish | Reversal | -0.631% / -0.749% / -1.112% | Liquidity sweep / reversal | 73.2% | 21.6% | 5.2% | 2.08x | 0.284% / 1.151% |
| 2026-08-18 07:00 | 4.29x | Small-body bullish | Flat / fading | -0.268% / -0.339% / -0.047% | Position building in range | 41.2% | 24.6% | 34.2% | 4.37x | 0.055% / 0.442% |
| 2026-08-18 08:00 | 2.77x | Full-bodied bullish | Reversal | 0.071% / -0.118% / -0.245% | Liquidity sweep / reversal | 68.8% | 15.6% | 15.6% | 0.91x | 0.134% / 0.324% |
| 2026-08-18 09:30 | 2.65x | Full-bodied bullish | Reversal | -0.220% / -0.094% / -0.858% | Liquidity sweep / reversal | 62.2% | 27.0% | 10.8% | 1.78x | 0.094% / 0.874% |
| 2026-08-18 10:30 | 3.94x | Full-bodied bearish | Reversal | 0.183% / 0.167% / 1.247% | Liquidity sweep / reversal | 87.3% | 10.9% | 1.8% | 2.42x | 0.056% / 1.541% |
| 2026-08-18 11:30 | 2.82x | Full-bodied bullish | Impulse / continuation | 0.635% / 0.494% / 1.875% | True breakout | 64.5% | 34.6% | 0.9% | 2.22x | 2.134% / 0.008% |
| 2026-08-18 11:45 | 3.89x | Full-bodied bullish | Impulse / continuation | -0.140% / 0.998% / 0.834% | True breakout | 71.3% | 28.7% | 0.0% | 2.15x | 1.489% / 0.273% |
| 2026-08-18 12:15 | 4.05x | Full-bodied bullish | Impulse / continuation | 0.232% / -0.162% / -0.239% | True breakout | 93.6% | 0.6% | 5.7% | 2.59x | 0.486% / 0.594% |
| 2026-08-18 12:30 | 3.22x | Bearish pin-bar / upper rejection | Reversal | -0.393% / -0.670% / 0.015% | Liquidity sweep / reversal | 42.1% | 43.4% | 14.5% | 1.09x | 0.054% / 0.824% |
| 2026-08-18 15:30 | 2.13x | Full-bodied bearish | Flat / fading | 0.233% / 0.559% / 0.295% | Weak move without breakout | 84.8% | 4.3% | 10.9% | 2.74x | 0.310% / 0.776% |
| 2026-08-19 07:00 | 4.46x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.115% / 0.122% / -0.199% | True breakout | 25.2% | 18.7% | 56.1% | 5.72x | 0.351% / 0.214% |
| 2026-08-19 07:15 | 3.08x | Small-body bullish | Reversal | 0.008% / -0.122% / -0.450% | Liquidity sweep / reversal | 32.6% | 27.9% | 39.5% | 1.74x | 0.236% / 0.671% |
| 2026-08-19 07:30 | 2.93x | Bearish pin-bar / upper rejection | Reversal | -0.130% / -0.320% / -0.305% | Liquidity sweep / reversal | 1.8% | 54.5% | 43.6% | 2.06x | 0.023% / 0.679% |
| 2026-08-19 10:15 | 4.18x | Full-bodied bearish | Impulse / continuation | -0.224% / 0.008% / -0.464% | True breakout | 93.5% | 0.0% | 6.5% | 1.96x | 0.672% / 0.201% |
| 2026-08-19 11:00 | 2.72x | Full-bodied bearish | Reversal | 0.078% / 0.295% / 0.505% | Liquidity sweep / reversal | 68.6% | 22.9% | 8.6% | 2.19x | 0.132% / 0.847% |
| 2026-08-19 15:00 | 2.29x | Full-bodied bullish | Impulse / continuation | 0.300% / 0.046% / -0.092% | True breakout | 83.1% | 16.9% | 0.0% | 2.46x | 0.569% / 0.108% |
| 2026-08-20 07:00 | 5.68x | Bullish pin-bar / lower rejection | Flat / fading | 0.069% / -0.085% / -0.139% | Position building in range | 19.0% | 38.0% | 43.0% | 4.94x | 0.185% / 0.162% |
| 2026-08-20 08:00 | 4.57x | Bearish pin-bar / upper rejection | Impulse -> reversal | -0.046% / 0.039% / 0.324% | False breakout | 25.6% | 74.4% | 0.0% | 1.78x | 0.177% / 0.470% |
| 2026-08-20 09:00 | 3.27x | Bearish pin-bar / upper rejection | Flat / fading | 0.038% / 0.015% / 0.238% | Weak move without breakout | 22.6% | 61.3% | 16.1% | 1.21x | 0.277% / 0.207% |
| 2026-08-20 10:15 | 5.62x | Full-bodied bullish | Impulse / continuation | 0.244% / 0.626% / 0.298% | True breakout | 72.9% | 7.1% | 20.0% | 2.06x | 0.626% / 0.023% |
| 2026-08-20 10:30 | 3.40x | Small-body bullish | Flat / fading | 0.381% / 0.221% / -0.152% | Weak move without breakout | 55.4% | 37.5% | 7.1% | 1.44x | 0.381% / 0.168% |
| 2026-08-20 12:15 | 2.23x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.153% / -0.374% / -1.945% | True breakout | 14.3% | 50.8% | 34.9% | 1.38x | 2.609% / 0.046% |
| 2026-08-20 13:00 | 6.47x | Full-bodied bearish | Impulse / continuation | 0.218% / 0.382% / -0.343% | True breakout | 91.8% | 0.0% | 8.2% | 5.01x | 0.842% / 0.577% |
| 2026-08-20 13:15 | 3.23x | Bullish pin-bar / lower rejection | Reversal | 0.163% / 0.039% / -0.303% | Liquidity sweep / reversal | 32.2% | 3.3% | 64.4% | 1.35x | 0.358% / 1.058% |
| 2026-08-20 17:30 | 2.60x | Full-bodied bearish | Flat / fading | 0.142% / 0.158% / 0.095% | Weak move without breakout | 67.0% | 0.0% | 33.0% | 1.40x | 0.633% / 0.482% |
| 2026-08-21 07:00 | 3.51x | Bullish pin-bar / lower rejection | Reversal | 0.039% / -0.063% / 0.079% | Liquidity sweep / reversal | 1.9% | 0.0% | 98.1% | 2.72x | 0.118% / 0.362% |
| 2026-08-21 07:15 | 2.54x | Bullish pin-bar / lower rejection | Reversal | -0.102% / -0.071% / -0.157% | Liquidity sweep / reversal | 15.6% | 28.1% | 56.3% | 1.49x | 0.079% / 0.401% |
| 2026-08-21 10:00 | 3.04x | Doji | Impulse / continuation | -0.512% / -0.331% / -0.236% | True breakout | 0.0% | 54.1% | 45.9% | 2.33x | 0.804% / 0.804% |
| 2026-08-21 10:15 | 6.01x | Full-bodied bearish | Flat / fading | 0.182% / -0.048% / 0.269% | Position building in range | 63.1% | 1.0% | 35.9% | 3.60x | 0.158% / 0.325% |
| 2026-08-21 11:30 | 6.22x | Small-body bullish | Flat / fading | -0.204% / -0.173% / 0.133% | Position building in range | 46.7% | 28.3% | 25.0% | 4.99x | 0.377% / 0.675% |
| 2026-08-21 11:45 | 3.18x | Bullish pin-bar / lower rejection | Reversal | 0.031% / 0.393% / 0.314% | Liquidity sweep / reversal | 28.3% | 6.5% | 65.2% | 1.90x | 0.393% / 0.582% |
| 2026-08-22 10:00 | 6.10x | Full-bodied bearish | Flat / fading | 0.110% / 0.024% / -0.126% | Weak move without breakout | 76.4% | 0.0% | 23.6% | 6.09x | 0.235% / 0.126% |
| 2026-08-22 12:30 | 3.20x | Bullish pin-bar / lower rejection | Reversal | 0.276% / 0.205% / 0.016% | Liquidity sweep / reversal | 59.2% | 0.0% | 40.8% | 1.70x | 0.024% / 0.300% |
| 2026-08-22 18:30 | 3.49x | Bullish pin-bar / lower rejection | Reversal | -0.079% / -0.087% / -0.543% | Liquidity sweep / reversal | 40.0% | 16.0% | 44.0% | 2.15x | 0.016% / 0.661% |
| 2026-08-23 10:15 | 4.17x | Full-bodied bearish | Flat / fading | 0.063% / 0.119% / 0.024% | Weak move without breakout | 72.2% | 0.0% | 27.8% | 4.55x | 0.040% / 0.348% |
| 2026-08-23 10:45 | 4.29x | Bearish pin-bar / upper rejection | Reversal | -0.055% / -0.095% / 0.032% | Liquidity sweep / reversal | 19.4% | 80.6% | 0.0% | 2.29x | 0.047% / 0.119% |
| 2026-08-24 07:00 | 34.29x | Bullish pin-bar / lower rejection | Flat / fading | 0.096% / -0.088% / 0.159% | Position building in range | 47.1% | 1.1% | 51.7% | 6.58x | 0.247% / 0.239% |
| 2026-08-24 07:15 | 9.94x | Bullish pin-bar / lower rejection | Reversal | -0.183% / -0.151% / -0.175% | Liquidity sweep / reversal | 31.4% | 15.7% | 52.9% | 2.70x | 0.143% / 0.326% |
| 2026-08-24 07:30 | 2.50x | Bullish pin-bar / lower rejection | Reversal | 0.032% / 0.247% / 0.008% | Liquidity sweep / reversal | 50.0% | 9.1% | 40.9% | 1.99x | 0.072% / 0.327% |
| 2026-08-24 08:00 | 3.26x | Small-body bullish | Reversal | -0.239% / -0.239% / -0.541% | Liquidity sweep / reversal | 54.0% | 20.0% | 26.0% | 1.92x | -0.008% / 0.739% |
| 2026-08-24 09:00 | 6.42x | Small-body bearish | Impulse / continuation | -0.200% / -0.424% / -0.280% | True breakout | 58.5% | 3.1% | 38.5% | 1.98x | 1.199% / 0.008% |
| 2026-08-24 09:15 | 10.05x | Bullish pin-bar / lower rejection | Flat / fading | -0.224% / 0.048% / 0.120% | Weak move without breakout | 16.7% | 0.0% | 83.3% | 4.11x | 0.801% / 0.320% |
| 2026-08-24 10:00 | 3.94x | Bullish pin-bar / lower rejection | Reversal | 0.200% / -0.048% / -0.056% | Liquidity sweep / reversal | 22.7% | 31.8% | 45.5% | 1.26x | 0.721% / 0.401% |
| 2026-08-24 10:15 | 4.03x | Bullish pin-bar / lower rejection | Reversal | -0.248% / -0.304% / -0.448% | Liquidity sweep / reversal | 20.0% | 17.9% | 62.1% | 2.47x | 0.200% / 0.760% |
| 2026-08-24 10:30 | 2.56x | Bullish pin-bar / lower rejection | Flat / fading | -0.056% / -0.008% / 0.032% | Weak move without breakout | 27.8% | 16.5% | 55.7% | 1.88x | 0.353% / 0.449% |
| 2026-08-24 16:45 | 2.60x | Bullish pin-bar / lower rejection | Reversal | -0.008% / 0.243% / 0.899% | Liquidity sweep / reversal | 21.8% | 21.8% | 56.4% | 1.57x | 0.194% / 1.045% |
| 2026-08-24 17:45 | 4.20x | Full-bodied bullish | Impulse / continuation | -0.241% / -0.161% / -0.594% | True breakout | 82.4% | 15.1% | 2.5% | 3.63x | 0.466% / 0.618% |
| 2026-08-25 07:00 | 4.39x | Full-bodied bullish | Impulse / continuation | 0.280% / 0.160% / 0.240% | True breakout | 91.9% | 6.5% | 1.6% | 2.99x | 0.520% / 0.008% |
| 2026-08-25 07:15 | 6.58x | Bearish pin-bar / upper rejection | Flat / fading | -0.120% / -0.112% / 0.040% | Position building in range | 54.5% | 45.5% | 0.0% | 2.86x | 0.040% / 0.287% |
| 2026-08-25 10:15 | 3.18x | Full-bodied bearish | Impulse / continuation | -0.048% / 0.040% / -0.048% | True breakout | 87.2% | 8.1% | 4.7% | 2.67x | 0.312% / 0.208% |
| 2026-08-25 12:30 | 2.61x | Full-bodied bearish | Flat / fading | 0.200% / 0.248% / 0.257% | Position building in range | 73.9% | 7.5% | 18.7% | 2.97x | 0.104% / 0.337% |
| 2026-08-25 17:30 | 8.46x | Full-bodied bullish | Impulse / continuation | 1.399% / 1.029% / 0.896% | True breakout | 64.4% | 35.6% | 0.0% | 3.58x | 1.768% / -0.024% |
| 2026-08-25 17:45 | 6.44x | Full-bodied bullish | Reversal | -0.364% / -0.519% / -1.380% | Liquidity sweep / reversal | 78.4% | 21.2% | 0.5% | 4.45x | 0.287% / 1.573% |
| 2026-08-25 18:00 | 3.17x | Small-body bearish | Impulse / continuation | -0.156% / -0.132% / -0.755% | True breakout | 47.5% | 35.6% | 16.8% | 1.63x | 1.283% / 0.187% |
| 2026-08-26 07:00 | 4.02x | Full-bodied bearish | Impulse / continuation | -0.040% / -0.047% / -0.261% | True breakout | 77.6% | 14.9% | 7.5% | 2.37x | 0.364% / 0.111% |
| 2026-08-26 13:00 | 6.65x | Full-bodied bearish | Flat / fading | 0.136% / 0.040% / 0.104% | Position building in range | 87.0% | 0.0% | 13.0% | 3.18x | 0.040% / 0.303% |
| 2026-08-26 14:30 | 3.30x | Full-bodied bearish | Flat / fading | 0.297% / 0.161% / 0.056% | Position building in range | 74.8% | 13.6% | 11.7% | 2.46x | 0.040% / 0.345% |
| 2026-08-26 16:00 | 2.92x | Full-bodied bullish | Impulse / continuation | -0.486% / -0.350% / -0.080% | True breakout | 81.1% | 8.1% | 10.8% | 2.43x | 0.557% / 0.565% |
| 2026-08-26 19:00 | 2.91x | Bullish pin-bar / lower rejection | Flat / fading | -0.064% / -0.008% / -0.177% | Position building in range | 9.7% | 36.6% | 53.8% | 1.65x | 0.233% / 0.161% |
| 2026-08-27 07:00 | 3.03x | Bearish pin-bar / upper rejection | Reversal | -0.040% / -0.249% / -0.200% | Liquidity sweep / reversal | 45.8% | 45.8% | 8.5% | 2.97x | 0.064% / 0.257% |
| 2026-08-27 10:00 | 7.73x | Small-body bearish | Reversal | 0.032% / -0.234% / 0.298% | Liquidity sweep / reversal | 25.8% | 36.0% | 38.2% | 2.90x | 0.274% / 0.427% |
| 2026-08-27 10:30 | 3.14x | Full-bodied bearish | Reversal | 0.210% / 0.533% / 1.744% | Liquidity sweep / reversal | 74.4% | 14.0% | 11.6% | 1.10x | 0.032% / 2.099% |
| 2026-08-27 11:00 | 2.80x | Small-body bullish | Impulse / continuation | 0.675% / 1.205% / 0.996% | True breakout | 54.2% | 22.2% | 23.6% | 1.88x | 1.558% / 0.185% |
| 2026-08-27 11:15 | 4.44x | Full-bodied bullish | Impulse / continuation | 0.527% / 0.080% / -0.024% | True breakout | 61.3% | 21.9% | 16.8% | 3.34x | 0.878% / 0.423% |
| 2026-08-27 11:30 | 3.84x | Full-bodied bullish | Reversal | -0.444% / -0.206% / -0.429% | Liquidity sweep / reversal | 60.4% | 39.6% | 0.0% | 2.28x | 0.040% / 0.944% |
| 2026-08-28 07:00 | 10.87x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.134% / 0.221% / 0.261% | True breakout | 6.6% | 9.6% | 83.8% | 7.77x | 0.364% / 0.103% |
| 2026-08-28 07:15 | 3.32x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.087% / 0.174% / 0.458% | True breakout | 30.4% | 63.0% | 6.5% | 1.43x | 0.584% / 0.237% |
| 2026-08-28 08:15 | 2.86x | Small-body bullish | Flat / fading | -0.126% / -0.189% / 0.055% | Position building in range | 58.3% | 22.2% | 19.4% | 2.11x | 0.102% / 0.220% |
| 2026-08-28 16:45 | 2.53x | Full-bodied bullish | Reversal | -0.445% / -0.683% / -1.104% | Liquidity sweep / reversal | 79.6% | 5.4% | 15.1% | 3.09x | 0.008% / 1.255% |
| 2026-08-28 17:45 | 3.01x | Small-body bearish | Flat / fading | 0.104% / -0.016% / 0.161% | Weak move without breakout | 58.0% | 4.0% | 38.0% | 1.16x | 0.120% / 0.329% |
| 2026-08-29 14:30 | 4.31x | Full-bodied bearish | Flat / fading | 0.016% / -0.008% / 0.008% | Position building in range | 72.4% | 6.9% | 20.7% | 3.30x | 0.016% / 0.040% |
| 2026-08-30 10:00 | 9.38x | Bearish pin-bar / upper rejection | Flat / fading | 0.016% / -0.024% / -0.032% | Position building in range | 16.1% | 51.6% | 32.3% | 5.42x | 0.072% / 0.040% |
| 2026-08-30 18:30 | 3.40x | Full-bodied bearish | Reversal | 0.000% / 0.048% / -0.008% | Liquidity sweep / reversal | 83.3% | 0.0% | 16.7% | 1.09x | 0.224% / 0.208% |
| 2026-08-31 07:00 | 31.72x | Small-body bearish | Reversal | 0.072% / 0.265% / 0.361% | Liquidity sweep / reversal | 29.6% | 37.0% | 33.3% | 10.65x | 0.064% / 0.417% |
| 2026-08-31 07:15 | 3.01x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.192% / 0.056% / 0.208% | True breakout | 38.1% | 19.0% | 42.9% | 2.49x | 0.345% / 0.088% |
| 2026-08-31 07:30 | 4.53x | Small-body bullish | Impulse / continuation | -0.136% / 0.096% / 0.208% | True breakout | 51.0% | 28.6% | 20.4% | 5.16x | 0.304% / 0.200% |
| 2026-08-31 07:45 | 2.90x | Full-bodied bearish | Reversal | 0.232% / 0.152% / 0.328% | Liquidity sweep / reversal | 65.4% | 3.8% | 30.8% | 2.08x | 0.016% / 0.513% |
| 2026-08-31 08:00 | 5.44x | Full-bodied bullish | Impulse / continuation | -0.080% / 0.112% / 0.048% | True breakout | 76.3% | 18.4% | 5.3% | 2.74x | 0.280% / 0.096% |
| 2026-08-31 08:30 | 6.04x | Full-bodied bullish | Flat / fading | -0.016% / -0.064% / 0.104% | Weak move without breakout | 65.8% | 31.6% | 2.6% | 2.22x | 0.168% / 0.128% |
| 2026-08-31 08:45 | 3.07x | Bearish pin-bar / upper rejection | Reversal | -0.048% / 0.016% / 0.008% | Liquidity sweep / reversal | 8.3% | 87.5% | 4.2% | 1.23x | 0.112% / 0.160% |
| 2026-08-31 10:00 | 2.47x | Bearish pin-bar / upper rejection | Flat / fading | -0.032% / -0.040% / 0.096% | Position building in range | 35.4% | 41.5% | 23.1% | 2.38x | 0.215% / 0.167% |
| 2026-08-31 17:45 | 3.00x | Small-body bullish | Impulse / continuation | 1.300% / 1.444% / 1.771% | True breakout | 58.3% | 20.8% | 20.8% | 3.34x | 2.361% / 0.152% |
| 2026-08-31 18:00 | 10.33x | Full-bodied bullish | Impulse / continuation | 0.142% / 0.677% / 0.118% | True breakout | 86.6% | 2.7% | 10.7% | 7.40x | 1.047% / 0.197% |
| 2026-08-31 18:15 | 7.95x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.535% / 0.322% / -0.016% | True breakout | 15.5% | 79.4% | 5.2% | 2.66x | 0.904% / 0.338% |
| 2026-08-31 18:30 | 5.57x | Small-body bullish | Reversal | -0.211% / -0.555% / -0.454% | Liquidity sweep / reversal | 57.1% | 6.7% | 36.1% | 2.80x | 0.368% / 0.673% |
| 2026-08-31 18:45 | 3.33x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.345% / -0.337% / -0.564% | True breakout | 25.0% | 55.4% | 19.6% | 1.85x | 0.611% / 0.078% |
| 2026-09-01 07:00 | 5.86x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.173% / -0.384% / -0.361% | True breakout | 26.2% | 21.5% | 52.3% | 3.65x | 0.502% / 0.078% |
| 2026-09-01 07:30 | 2.62x | Full-bodied bearish | Flat / fading | 0.150% / 0.024% / 0.165% | Weak move without breakout | 61.9% | 2.4% | 35.7% | 1.75x | 0.055% / 0.315% |
| 2026-09-01 10:15 | 4.18x | Full-bodied bullish | Impulse / continuation | -0.133% / -0.117% / 0.469% | True breakout | 82.8% | 17.2% | 0.0% | 2.79x | 0.547% / 0.383% |
| 2026-09-01 11:15 | 2.53x | Full-bodied bullish | Flat / fading | -0.194% / -0.194% / -0.241% | Weak move without breakout | 77.1% | 20.8% | 2.1% | 1.42x | 0.109% / 0.311% |
| 2026-09-01 15:15 | 2.00x | Bullish pin-bar / lower rejection | Reversal | -0.179% / -0.413% / -0.062% | Liquidity sweep / reversal | 28.3% | 28.3% | 43.3% | 1.51x | 0.109% / 0.686% |
| 2026-09-01 15:45 | 2.13x | Bullish pin-bar / lower rejection | Reversal | 0.196% / 0.352% / 0.149% | Liquidity sweep / reversal | 35.8% | 21.0% | 43.2% | 1.85x | 0.180% / 0.376% |
| 2026-09-01 20:45 | 3.14x | Full-bodied bearish | Impulse / continuation | 0.141% / -0.800% / -0.643% | True breakout | 81.9% | 0.0% | 18.1% | 2.86x | 1.044% / 0.157% |
| 2026-09-01 21:15 | 6.84x | Full-bodied bearish | Flat / fading | 0.158% / 0.158% / -0.119% | Position building in range | 78.8% | 0.0% | 21.2% | 3.90x | 0.214% / 0.269% |
| 2026-09-02 18:30 | 2.82x | Full-bodied bullish | Impulse / continuation | 0.000% / 0.016% / -0.055% | True breakout | 78.9% | 21.1% | 0.0% | 1.32x | 0.338% / 0.157% |
| 2026-09-02 18:45 | 2.69x | Bearish pin-bar / upper rejection | Flat / fading | 0.016% / -0.118% / -0.016% | Weak move without breakout | 3.8% | 78.8% | 17.3% | 1.87x | 0.157% / 0.220% |
| 2026-09-03 07:00 | 9.21x | Bearish pin-bar / upper rejection | Flat / fading | 0.298% / 0.267% / 0.212% | Position building in range | 8.9% | 78.2% | 12.9% | 8.42x | 0.376% / -0.008% |
| 2026-09-03 07:15 | 3.64x | Full-bodied bullish | Flat / fading | -0.031% / -0.031% / 0.086% | Weak move without breakout | 78.7% | 21.3% | 0.0% | 2.62x | 0.094% / 0.109% |
| 2026-09-03 12:15 | 3.66x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.126% / 0.024% / 0.094% | True breakout | 26.6% | 68.8% | 4.7% | 2.53x | 0.455% / 0.306% |
| 2026-09-03 12:30 | 4.55x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.102% / -0.016% / 0.235% | True breakout | 23.0% | 0.0% | 77.0% | 2.60x | 0.313% / 0.196% |
| 2026-09-03 13:45 | 5.94x | Full-bodied bullish | Flat / fading | -0.093% / 0.008% / 0.210% | Weak move without breakout | 75.0% | 25.0% | 0.0% | 2.40x | 0.335% / 0.171% |
| 2026-09-03 20:00 | 5.84x | Full-bodied bullish | Flat / fading | 0.000% / 0.061% / 0.253% | Weak move without breakout | 80.4% | 14.9% | 4.8% | 6.24x | 0.368% / 0.199% |
| 2026-09-04 09:00 | 6.71x | Full-bodied bullish | Flat / fading | 0.023% / 0.023% / -0.091% | Weak move without breakout | 75.7% | 23.5% | 0.7% | 5.30x | 0.426% / 0.266% |
| 2026-09-04 09:45 | 2.77x | Bearish pin-bar / upper rejection | Reversal | -0.289% / -0.144% / -0.076% | Liquidity sweep / reversal | 41.8% | 54.5% | 3.6% | 1.51x | 0.053% / 0.463% |
| 2026-09-04 11:30 | 3.57x | Full-bodied bullish | Flat / fading | -0.241% / -0.505% / -0.271% | Position building in range | 76.4% | 7.3% | 16.4% | 2.46x | 0.023% / 0.520% |
| 2026-09-04 23:30 | 6.03x | Full-bodied bullish | Impulse / continuation | -0.068% / 0.181% / 0.431% | True breakout | 75.6% | 24.4% | 0.0% | 3.07x | 0.786% / 0.128% |
| 2026-09-05 10:00 | 4.21x | Bearish pin-bar / upper rejection | Flat / fading | 0.113% / 0.038% / -0.008% | Position building in range | 23.0% | 71.3% | 5.7% | 4.54x | 0.128% / 0.105% |
| 2026-09-05 11:30 | 2.75x | Small-body bearish | Impulse / continuation | -0.075% / -0.098% / -0.747% | True breakout | 53.3% | 8.9% | 37.8% | 1.80x | 1.350% / 0.000% |
| 2026-09-05 12:30 | 5.44x | Bullish pin-bar / lower rejection | Flat / fading | 0.023% / 0.030% / 0.144% | Position building in range | 39.7% | 3.5% | 56.7% | 4.68x | 0.167% / 0.175% |
| 2026-09-05 14:45 | 3.24x | Full-bodied bullish | Flat / fading | -0.023% / 0.023% / 0.000% | Weak move without breakout | 97.3% | 2.7% | 0.0% | 2.26x | 0.083% / 0.091% |
| 2026-09-06 10:00 | 2.63x | Doji / lower rejection | Impulse / continuation | 0.008% / -0.038% / -0.667% | True breakout | 0.0% | 21.1% | 78.9% | 2.30x | 0.781% / 0.781% |
| 2026-09-06 10:45 | 4.01x | Full-bodied bearish | Impulse / continuation | -0.350% / -0.114% / -0.068% | True breakout | 81.8% | 6.8% | 11.4% | 2.43x | 0.479% / 0.076% |
| 2026-09-06 11:00 | 4.66x | Full-bodied bearish | Flat / fading | 0.237% / 0.175% / 0.305% | Weak move without breakout | 65.7% | 12.9% | 21.4% | 3.44x | 0.130% / 0.427% |
| 2026-09-06 11:15 | 2.77x | Small-body bullish | Flat / fading | -0.061% / 0.046% / 0.175% | Weak move without breakout | 60.0% | 4.0% | 36.0% | 2.08x | 0.190% / 0.099% |
| 2026-09-06 11:30 | 3.50x | Bearish pin-bar / upper rejection | Reversal | 0.107% / 0.129% / 0.183% | Liquidity sweep / reversal | 21.1% | 65.8% | 13.2% | 1.44x | 0.030% / 0.259% |
| 2026-09-06 17:45 | 5.15x | Full-bodied bearish | Impulse / continuation | 0.069% / 0.053% / -0.824% | True breakout | 77.5% | 2.5% | 20.0% | 3.81x | 0.969% / 0.130% |
| 2026-09-06 18:15 | 3.00x | Bullish pin-bar / lower rejection | Reversal | -0.107% / -0.877% / -0.572% | Liquidity sweep / reversal | 4.0% | 20.0% | 76.0% | 2.05x | 0.030% / 1.022% |
| 2026-09-06 18:45 | 18.93x | Full-bodied bearish | Flat / fading | 0.292% / 0.308% / 0.408% | Position building in range | 83.5% | 0.8% | 15.7% | 9.01x | -0.192% / 0.462% |
| 2026-09-07 07:00 | 3.73x | Bearish pin-bar / upper rejection | Reversal | 0.054% / 0.100% / -0.054% | Liquidity sweep / reversal | 14.7% | 55.9% | 29.4% | 1.39x | 0.153% / 0.161% |
| 2026-09-07 17:45 | 4.11x | Full-bodied bullish | Flat / fading | -0.114% / -0.258% / -0.083% | Weak move without breakout | 71.2% | 11.5% | 17.3% | 2.51x | 0.129% / 0.295% |
| 2026-09-08 07:00 | 2.99x | Bullish pin-bar / lower rejection | Reversal | -0.023% / -0.257% / -0.219% | Liquidity sweep / reversal | 43.7% | 9.4% | 46.9% | 1.95x | 0.015% / 0.333% |
| 2026-09-08 09:00 | 3.57x | Full-bodied bearish | Impulse / continuation | 0.000% / 0.046% / -0.076% | True breakout | 87.9% | 0.0% | 12.1% | 1.51x | 0.213% / 0.152% |
| 2026-09-08 09:15 | 2.89x | Bearish pin-bar / upper rejection | Reversal | 0.046% / 0.015% / -0.373% | Liquidity sweep / reversal | 3.6% | 71.4% | 25.0% | 1.25x | 0.145% / 0.380% |
| 2026-09-08 10:30 | 2.64x | Bullish pin-bar / lower rejection | Reversal | 0.038% / 0.306% / 0.199% | Liquidity sweep / reversal | 21.6% | 8.1% | 70.3% | 1.39x | 0.015% / 0.390% |
| 2026-09-08 11:45 | 3.25x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.175% / 0.441% / 0.304% | True breakout | 33.8% | 40.0% | 26.2% | 2.27x | 0.571% / 0.023% |
| 2026-09-08 13:00 | 2.07x | Full-bodied bullish | Flat / fading | -0.113% / -0.045% / 0.098% | Weak move without breakout | 65.3% | 26.4% | 8.3% | 2.10x | 0.325% / 0.181% |
| 2026-09-08 13:45 | 2.00x | Small-body bullish | Flat / fading | -0.060% / 0.234% / -0.106% | Weak move without breakout | 44.1% | 37.3% | 18.6% | 1.59x | 0.279% / 0.159% |
| 2026-09-08 14:00 | 2.02x | Bearish pin-bar / upper rejection | Reversal | 0.295% / 0.091% / -0.068% | Liquidity sweep / reversal | 30.3% | 48.5% | 21.2% | 0.86x | 0.166% / 0.340% |
| 2026-09-08 16:15 | 2.09x | Full-bodied bearish | Impulse / continuation | -0.114% / 0.015% / -0.568% | True breakout | 65.3% | 0.0% | 34.7% | 2.16x | 0.758% / 0.447% |
| 2026-09-08 17:15 | 3.70x | Small-body bearish | Impulse / continuation | -0.267% / -0.335% / -0.259% | True breakout | 45.3% | 39.0% | 15.7% | 4.61x | 0.617% / 0.267% |
| 2026-09-09 07:00 | 2.87x | Full-bodied bearish | Flat / fading | 0.000% / -0.031% / -0.008% | Weak move without breakout | 69.6% | 0.0% | 30.4% | 1.51x | 0.122% / 0.084% |
| 2026-09-09 08:30 | 3.25x | Small-body bearish | Impulse / continuation | -0.008% / -0.008% / -0.214% | True breakout | 52.6% | 7.9% | 39.5% | 2.71x | 0.237% / 0.107% |
| 2026-09-09 08:45 | 2.53x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / -0.038% / -0.076% | Weak move without breakout | 4.0% | 16.0% | 80.0% | 1.57x | 0.229% / 0.115% |
| 2026-09-09 09:00 | 2.90x | Bullish pin-bar / lower rejection | Reversal | -0.038% / -0.207% / -0.084% | Liquidity sweep / reversal | 3.8% | 23.1% | 73.1% | 1.49x | 0.115% / 0.229% |
| 2026-09-09 09:30 | 3.20x | Full-bodied bearish | Flat / fading | 0.130% / 0.123% / 0.092% | Weak move without breakout | 81.5% | 7.4% | 11.1% | 1.42x | 0.015% / 0.261% |
| 2026-09-09 10:15 | 4.91x | Bearish pin-bar / upper rejection | Reversal | -0.008% / 0.306% / 0.077% | Liquidity sweep / reversal | 5.9% | 50.0% | 44.1% | 1.61x | 0.084% / 0.475% |
| 2026-09-09 10:45 | 2.84x | Full-bodied bullish | Flat / fading | -0.145% / -0.229% / -0.145% | Weak move without breakout | 69.5% | 13.6% | 16.9% | 2.61x | 0.168% / 0.275% |
| 2026-09-09 12:15 | 5.73x | Full-bodied bearish | Impulse / continuation | -0.185% / -0.077% / -0.292% | True breakout | 74.4% | 0.0% | 25.6% | 2.84x | 0.508% / 0.000% |
| 2026-09-09 12:30 | 2.99x | Bullish pin-bar / lower rejection | Flat / fading | 0.108% / 0.108% / -0.123% | Weak move without breakout | 36.4% | 0.0% | 63.6% | 2.00x | 0.455% / 0.139% |
| 2026-09-09 17:45 | 3.87x | Full-bodied bearish | Reversal | 0.278% / 0.495% / 0.410% | Liquidity sweep / reversal | 62.5% | 2.5% | 35.0% | 2.37x | 0.116% / 0.502% |
| 2026-09-10 09:00 | 3.43x | Full-bodied bearish | Flat / fading | 0.131% / 0.185% / 0.216% | Weak move without breakout | 77.5% | 0.0% | 22.5% | 2.99x | 0.023% / 0.247% |
| 2026-09-10 10:15 | 3.67x | Small-body bullish | Impulse / continuation | 0.023% / -0.046% / 0.208% | True breakout | 57.1% | 28.6% | 14.3% | 1.38x | 0.315% / 0.123% |
| 2026-09-10 11:00 | 6.13x | Full-bodied bullish | Impulse / continuation | -0.100% / -0.153% / 0.031% | True breakout | 93.7% | 2.1% | 4.2% | 2.90x | 0.307% / 0.222% |
| 2026-09-10 12:00 | 3.08x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / -0.008% / -0.069% | Position building in range | 28.6% | 57.1% | 14.3% | 3.14x | 0.038% / 0.153% |
| 2026-09-10 15:30 | 3.95x | Bearish pin-bar / upper rejection | Reversal | -0.176% / -0.061% / -0.207% | Liquidity sweep / reversal | 9.3% | 69.8% | 20.9% | 1.81x | 0.061% / 0.268% |
| 2026-09-10 17:45 | 2.78x | Bearish pin-bar / upper rejection | Reversal | 0.191% / 0.145% / 0.396% | Liquidity sweep / reversal | 5.1% | 53.8% | 41.0% | 1.23x | 0.000% / 0.511% |
| 2026-09-10 18:00 | 4.02x | Bearish pin-bar / upper rejection | Flat / fading | -0.046% / 0.122% / -0.030% | Weak move without breakout | 48.0% | 50.0% | 2.0% | 1.57x | 0.320% / 0.129% |
| 2026-09-11 07:00 | 6.86x | Small-body bearish | Flat / fading | -0.008% / -0.015% / 0.008% | Position building in range | 53.4% | 14.8% | 31.8% | 6.42x | 0.053% / 0.092% |
| 2026-09-11 09:30 | 3.86x | Full-bodied bearish | Impulse / continuation | 0.130% / -0.215% / -0.008% | True breakout | 76.9% | 1.5% | 21.5% | 2.92x | 0.368% / 0.176% |
| 2026-09-11 10:00 | 2.77x | Full-bodied bearish | Flat / fading | 0.123% / 0.207% / 0.123% | Weak move without breakout | 67.6% | 2.9% | 29.4% | 2.52x | 0.238% / 0.284% |
| 2026-09-11 11:00 | 4.29x | Bullish pin-bar / lower rejection | Flat / fading | -0.115% / -0.368% / -0.238% | Weak move without breakout | 2.0% | 2.0% | 95.9% | 1.84x | 0.506% / 0.084% |
| 2026-09-11 13:15 | 4.19x | Small-body bullish | Reversal | -1.019% / -1.217% / -0.601% | Liquidity sweep / reversal | 50.8% | 24.6% | 24.6% | 5.76x | 0.304% / 1.703% |
| 2026-09-11 13:30 | 10.86x | Small-body bearish | Flat / fading | -0.200% / -0.046% / 0.069% | Weak move without breakout | 53.6% | 16.0% | 30.4% | 5.50x | 0.691% / 0.638% |
| 2026-09-11 13:45 | 2.57x | Bullish pin-bar / lower rejection | Reversal | 0.154% / 0.624% / 0.523% | Liquidity sweep / reversal | 27.8% | 1.1% | 71.1% | 1.54x | 0.300% / 0.839% |
| 2026-09-11 14:15 | 2.70x | Full-bodied bullish | Flat / fading | -0.352% / -0.099% / -0.459% | Weak move without breakout | 63.5% | 29.2% | 7.3% | 1.45x | 0.000% / 0.796% |
| 2026-09-14 07:00 | 10.66x | Bearish pin-bar / upper rejection | Flat / fading | -0.046% / -0.046% / 0.076% | Weak move without breakout | 17.0% | 51.1% | 31.9% | 3.41x | 0.137% / 0.228% |
| 2026-09-14 07:15 | 4.45x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.061% / 0.168% | Liquidity sweep / reversal | 15.8% | 21.1% | 63.2% | 2.27x | 0.107% / 0.343% |
| 2026-09-14 08:15 | 2.95x | Bearish pin-bar / upper rejection | Reversal | 0.015% / 0.046% / 0.030% | Liquidity sweep / reversal | 5.7% | 65.7% | 28.6% | 1.82x | 0.122% / 0.122% |
| 2026-09-14 10:15 | 6.21x | Full-bodied bullish | Flat / fading | -0.091% / -0.128% / -0.174% | Weak move without breakout | 89.7% | 10.3% | 0.0% | 2.70x | 0.121% / 0.264% |
| 2026-09-14 16:00 | 6.90x | Bullish pin-bar / lower rejection | Flat / fading | -0.236% / -0.243% / -0.205% | Position building in range | 38.7% | 9.4% | 51.9% | 4.18x | 0.410% / 0.008% |
| 2026-09-14 18:00 | 7.17x | Full-bodied bullish | Impulse / continuation | 0.603% / 0.362% / 0.204% | True breakout | 85.0% | 10.6% | 4.4% | 5.01x | 1.071% / 0.015% |
| 2026-09-14 18:15 | 6.94x | Bearish pin-bar / upper rejection | Flat / fading | -0.240% / -0.090% / -0.195% | Position building in range | 54.2% | 43.1% | 2.8% | 3.53x | 0.165% / 0.577% |
| 2026-09-15 10:00 | 3.34x | Bearish pin-bar / upper rejection | Reversal | -0.075% / -0.218% / -0.654% | Liquidity sweep / reversal | 35.0% | 42.5% | 22.5% | 1.47x | 0.038% / 0.699% |
| 2026-09-15 10:30 | 2.55x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.173% / -0.437% / -0.384% | True breakout | 54.3% | 2.9% | 42.9% | 1.19x | 0.482% / 0.038% |
| 2026-09-15 11:45 | 2.80x | Full-bodied bearish | Reversal | 0.061% / 0.136% / 0.212% | Liquidity sweep / reversal | 60.4% | 7.5% | 32.1% | 1.77x | 0.068% / 0.493% |
| 2026-09-15 13:15 | 5.01x | Bearish pin-bar / upper rejection | Flat / fading | -0.053% / -0.248% / -0.459% | Position building in range | 51.8% | 45.3% | 2.9% | 4.31x | 0.158% / 0.534% |
| 2026-09-15 18:45 | 2.67x | Bullish pin-bar / lower rejection | Flat / fading | 0.000% / -0.061% / -0.061% | Weak move without breakout | 27.3% | 31.8% | 40.9% | 1.66x | 0.190% / 0.083% |
| 2026-09-16 07:00 | 4.02x | Bullish pin-bar / lower rejection | Reversal | 0.038% / 0.213% / 0.213% | Liquidity sweep / reversal | 8.3% | 36.1% | 55.6% | 2.22x | 0.023% / 0.251% |
| 2026-09-16 08:15 | 2.60x | Full-bodied bullish | Reversal | -0.098% / -0.045% / -0.182% | Liquidity sweep / reversal | 70.4% | 7.4% | 22.2% | 1.34x | 0.000% / 0.288% |
| 2026-09-16 10:15 | 2.62x | Small-body bearish | Impulse / continuation | 0.099% / -0.076% / -0.091% | True breakout | 59.3% | 22.2% | 18.5% | 1.33x | 0.243% / 0.175% |
| 2026-09-16 10:30 | 3.28x | Bullish pin-bar / lower rejection | Reversal | -0.175% / -0.258% / -0.289% | Liquidity sweep / reversal | 29.2% | 20.8% | 50.0% | 2.27x | 0.000% / 0.342% |
| 2026-09-16 12:30 | 2.56x | Full-bodied bearish | Impulse / continuation | 0.031% / -0.115% / -0.199% | True breakout | 91.7% | 2.1% | 6.3% | 1.81x | 0.298% / 0.107% |
| 2026-09-16 13:00 | 3.05x | Full-bodied bearish | Impulse / continuation | 0.023% / -0.084% / -0.321% | True breakout | 65.5% | 0.0% | 34.5% | 1.03x | 0.367% / 0.191% |
| 2026-09-16 14:15 | 3.43x | Full-bodied bearish | Reversal | -0.031% / -0.031% / 0.077% | Liquidity sweep / reversal | 75.0% | 13.9% | 11.1% | 1.17x | 0.200% / 0.308% |
| 2026-09-16 14:30 | 2.29x | Bullish pin-bar / lower rejection | Reversal | 0.000% / 0.262% / 0.123% | Liquidity sweep / reversal | 5.0% | 35.0% | 60.0% | 0.63x | 0.169% / 0.339% |
| 2026-09-16 14:45 | 2.20x | Doji / lower rejection | Impulse / continuation | 0.262% / 0.108% / 0.185% | True breakout | 0.0% | 26.7% | 73.3% | 0.99x | 0.339% / 0.339% |
| 2026-09-16 15:00 | 2.81x | Full-bodied bullish | Flat / fading | -0.154% / -0.138% / -0.177% | Position building in range | 67.3% | 19.2% | 13.5% | 1.69x | 0.054% / 0.276% |
| 2026-09-16 16:30 | 2.27x | Full-bodied bearish | Impulse / continuation | -0.240% / -0.417% / -0.479% | True breakout | 75.0% | 22.7% | 2.3% | 1.27x | 0.850% / 0.031% |
| 2026-09-16 17:00 | 3.67x | Bullish pin-bar / lower rejection | Flat / fading | -0.202% / -0.062% / -0.489% | Weak move without breakout | 30.5% | 1.2% | 68.3% | 2.24x | 0.660% / 0.093% |
| 2026-09-16 23:30 | 2.88x | Bullish pin-bar / lower rejection | Impulse -> reversal | -0.023% / -0.485% / 0.180% | False breakout | 27.6% | 0.0% | 72.4% | 2.94x | 0.485% / 0.344% |
| 2026-09-17 07:00 | 4.80x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.156% / 0.156% / 0.133% | True breakout | 34.8% | 19.7% | 45.5% | 2.56x | 0.320% / 0.125% |
| 2026-09-17 07:15 | 2.89x | Bearish pin-bar / upper rejection | Flat / fading | 0.000% / -0.055% / -0.125% | Weak move without breakout | 46.5% | 48.8% | 4.7% | 1.47x | 0.047% / 0.281% |
| 2026-09-17 10:00 | 5.73x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.140% / -0.780% / -0.577% | True breakout | 28.8% | 12.3% | 58.9% | 2.26x | 0.960% / 0.070% |
| 2026-09-17 10:30 | 6.42x | Full-bodied bearish | Flat / fading | 0.094% / 0.204% / 0.291% | Position building in range | 68.0% | 13.1% | 18.9% | 3.51x | 0.055% / 0.401% |
| 2026-09-17 13:15 | 4.17x | Full-bodied bearish | Impulse / continuation | 0.135% / -0.246% / -0.238% | True breakout | 71.4% | 0.0% | 28.6% | 2.16x | 0.595% / 0.214% |
| 2026-09-17 14:15 | 2.25x | Small-body bullish | Impulse / continuation | 0.119% / 0.095% / 0.644% | True breakout | 54.9% | 25.5% | 19.6% | 1.11x | 0.691% / 0.246% |
| 2026-09-18 07:00 | 6.57x | Full-bodied bullish | Impulse / continuation | 0.103% / 0.087% / 0.323% | True breakout | 62.9% | 22.9% | 14.3% | 4.07x | 0.434% / 0.087% |
| 2026-09-18 08:00 | 2.78x | Small-body bullish | Reversal | -0.173% / -0.228% / -0.260% | Liquidity sweep / reversal | 43.6% | 35.9% | 20.5% | 1.83x | 0.024% / 0.433% |
| 2026-09-18 14:00 | 2.13x | Full-bodied bullish | Flat / fading | -0.094% / -0.102% / 0.000% | Position building in range | 67.9% | 23.2% | 8.9% | 1.97x | 0.071% / 0.205% |
| 2026-09-18 21:45 | 2.75x | Full-bodied bearish | Flat / fading | 0.063% / 0.087% / 0.024% | Position building in range | 77.3% | 0.0% | 22.7% | 2.48x | 0.047% / 0.118% |
| 2026-09-18 23:00 | 4.47x | Full-bodied bearish | Flat / fading | 0.150% / 0.269% / 0.198% | Position building in range | 87.8% | 2.0% | 10.2% | 2.94x | 0.000% / 0.269% |
| 2026-09-19 10:00 | 2.76x | Bullish pin-bar / lower rejection | Flat / fading | -0.047% / -0.040% / 0.016% | Position building in range | 34.9% | 0.0% | 65.1% | 2.45x | 0.055% / 0.047% |
| 2026-09-20 18:45 | 4.49x | Full-bodied bearish | Reversal | 0.047% / 0.142% / 0.546% | Liquidity sweep / reversal | 71.4% | 0.0% | 28.6% | 2.51x | 0.040% / 0.593% |
| 2026-09-21 07:00 | 21.63x | Bullish pin-bar / lower rejection | Impulse / continuation | 0.126% / 0.403% / 0.655% | True breakout | 20.8% | 4.2% | 75.0% | 7.00x | 0.655% / 0.024% |
| 2026-09-21 07:15 | 12.80x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.276% / 0.166% / 0.426% | True breakout | 43.7% | 40.6% | 15.6% | 6.59x | 0.552% / 0.016% |
| 2026-09-21 07:30 | 15.53x | Full-bodied bullish | Impulse / continuation | -0.110% / 0.252% / 0.204% | True breakout | 81.4% | 14.0% | 4.7% | 6.27x | 0.275% / 0.157% |
| 2026-09-21 07:45 | 5.13x | Small-body bearish | Reversal | 0.362% / 0.260% / 0.283% | Liquidity sweep / reversal | 50.0% | 28.6% | 21.4% | 2.88x | 0.008% / 0.472% |
| 2026-09-21 08:00 | 4.85x | Full-bodied bullish | Impulse / continuation | -0.102% / -0.047% / -0.094% | True breakout | 97.9% | 0.0% | 2.1% | 4.09x | 0.110% / 0.180% |
| 2026-09-21 08:45 | 2.54x | Bearish pin-bar / upper rejection | Impulse / continuation | -0.016% / -0.079% / -0.157% | True breakout | 13.3% | 66.7% | 20.0% | 1.78x | 0.251% / 0.031% |
| 2026-09-21 10:00 | 4.65x | Small-body bearish | Impulse / continuation | 0.039% / -0.110% / -0.079% | True breakout | 56.0% | 12.0% | 32.0% | 1.03x | 0.409% / 0.079% |
| 2026-09-21 10:45 | 2.49x | Full-bodied bearish | Reversal | 0.205% / -0.284% / 0.047% | Liquidity sweep / reversal | 70.6% | 5.9% | 23.5% | 1.24x | 0.324% / 0.237% |
| 2026-09-21 11:00 | 2.68x | Small-body bullish | Reversal | -0.488% / -0.362% / -0.268% | Liquidity sweep / reversal | 56.5% | 8.7% | 34.8% | 1.67x | 0.000% / 0.528% |
| 2026-09-21 11:15 | 3.43x | Full-bodied bearish | Flat / fading | 0.127% / 0.333% / 0.238% | Position building in range | 92.5% | 0.0% | 7.5% | 2.42x | 0.024% / 0.372% |
| 2026-09-21 17:15 | 4.08x | Bearish pin-bar / upper rejection | Impulse / continuation | 0.142% / 0.236% / 0.566% | True breakout | 48.6% | 48.6% | 2.7% | 1.62x | 1.156% / 0.000% |
| 2026-09-21 18:00 | 6.13x | Bearish pin-bar / upper rejection | Flat / fading | -0.180% / -0.164% / -0.273% | Position building in range | 54.8% | 45.2% | 0.0% | 4.57x | 0.008% / 0.375% |
| 2026-09-22 07:00 | 3.41x | Small-body bullish | Impulse / continuation | 0.242% / 0.172% / 0.211% | True breakout | 33.3% | 33.3% | 33.3% | 2.04x | 0.452% / 0.008% |
| 2026-09-22 07:15 | 5.47x | Bearish pin-bar / upper rejection | Flat / fading | -0.070% / -0.070% / -0.062% | Position building in range | 54.2% | 45.8% | 0.0% | 2.91x | 0.023% / 0.179% |
| 2026-09-22 09:00 | 2.54x | Full-bodied bullish | Flat / fading | -0.117% / -0.195% / -0.125% | Weak move without breakout | 74.3% | 14.3% | 11.4% | 1.41x | 0.000% / 0.304% |
| 2026-09-22 10:15 | 6.87x | Full-bodied bullish | Impulse / continuation | 0.023% / 0.054% / 0.178% | True breakout | 80.2% | 0.0% | 19.8% | 3.98x | 0.341% / 0.155% |
| 2026-09-22 10:30 | 4.77x | Bearish pin-bar / upper rejection | Flat / fading | 0.031% / 0.178% / 0.147% | Weak move without breakout | 5.8% | 61.5% | 32.7% | 1.69x | 0.318% / 0.178% |
| 2026-09-22 17:45 | 2.96x | Small-body bearish | Flat / fading | -0.116% / 0.116% / 0.155% | Weak move without breakout | 41.9% | 24.3% | 33.8% | 2.70x | 0.232% / 0.294% |
| 2026-09-23 07:00 | 3.28x | Full-bodied bullish | Flat / fading | -0.147% / -0.131% / -0.162% | Position building in range | 79.5% | 18.2% | 2.3% | 2.07x | 0.062% / 0.193% |
| 2026-09-23 09:15 | 3.49x | Bullish pin-bar / lower rejection | Impulse / continuation | -0.031% / 0.000% / 0.000% | True breakout | 10.0% | 40.0% | 50.0% | 0.60x | 0.279% / 0.124% |
| 2026-09-23 10:00 | 5.10x | Bearish pin-bar / upper rejection | Reversal | 0.163% / 0.202% / 0.062% | Liquidity sweep / reversal | 47.5% | 45.0% | 7.5% | 2.63x | 0.116% / 0.326% |
| 2026-09-23 12:00 | 3.50x | Full-bodied bearish | Impulse / continuation | 0.008% / -0.375% / -0.320% | True breakout | 61.5% | 28.2% | 10.3% | 3.52x | 0.687% / 0.273% |
| 2026-09-23 12:15 | 4.54x | Bullish pin-bar / lower rejection | Reversal | -0.382% / -0.577% / -0.297% | Liquidity sweep / reversal | 1.3% | 42.5% | 56.2% | 2.92x | 0.000% / 0.694% |
| 2026-09-23 12:30 | 3.88x | Bullish pin-bar / lower rejection | Flat / fading | -0.196% / 0.055% / 0.149% | Weak move without breakout | 57.8% | 1.2% | 41.0% | 2.55x | 0.313% / 0.180% |
| 2026-09-23 17:30 | 3.30x | Bearish pin-bar / upper rejection | Reversal | -0.195% / -0.094% / 0.945% | Liquidity sweep / reversal | 8.6% | 50.5% | 41.0% | 3.38x | 1.031% / 0.305% |
| 2026-09-23 18:15 | 3.37x | Full-bodied bullish | Impulse / continuation | 0.373% / 0.388% / 0.217% | True breakout | 92.4% | 5.4% | 2.2% | 2.56x | 0.520% / 0.124% |
| 2026-09-23 18:30 | 4.25x | Full-bodied bullish | Flat / fading | 0.015% / -0.077% / -0.217% | Weak move without breakout | 66.7% | 14.7% | 18.7% | 1.84x | 0.147% / 0.348% |
| 2026-09-23 22:00 | 3.42x | Full-bodied bullish | Flat / fading | -0.023% / 0.154% / 0.131% | Weak move without breakout | 84.0% | 12.3% | 3.8% | 4.38x | 0.223% / 0.108% |
| 2026-09-24 07:00 | 2.65x | Full-bodied bearish | Flat / fading | 0.085% / 0.154% / 0.177% | Position building in range | 85.7% | 0.0% | 14.3% | 2.58x | 0.023% / 0.270% |
| 2026-09-24 10:45 | 3.65x | Bearish pin-bar / upper rejection | Reversal | -0.422% / -0.560% / -0.552% | Liquidity sweep / reversal | 46.8% | 42.6% | 10.6% | 2.27x | 0.031% / 0.813% |
| 2026-09-24 11:00 | 5.60x | Bullish pin-bar / lower rejection | Flat / fading | -0.139% / -0.100% / -0.177% | Position building in range | 49.1% | 4.5% | 46.4% | 4.90x | 0.323% / 0.008% |
| 2026-09-24 11:15 | 3.75x | Bullish pin-bar / lower rejection | Insufficient data | 0.039% / 0.008% / n/a | Insufficient data | 44.2% | 0.0% | 55.8% | 1.50x | 0.177% / 0.054% |
| 2026-09-24 11:30 | 2.70x | Bullish pin-bar / lower rejection | Reversal | -0.031% / -0.077% / n/a | Liquidity sweep / reversal | 13.8% | 3.4% | 82.8% | 0.95x | 0.015% / 0.162% |
