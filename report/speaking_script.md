# Zoom recording script, about 10 minutes, 7 slides

Recording notes: 1080p, share the slides full screen, and speak to the numbers instead of reading
the slides. The script runs about 9 minutes 30 seconds, which leaves margin under the 15 minute cap.

## Slide 1 · Title and research question (55 s)

I reproduced TradingAgents, a multi-agent LLM trading framework, at commit 9fa1196, which is the
v0.7.1 tag, and I ran it with DeepSeek-V4.1-Flash in place of the paper's models. The course rules
allow that substitution as long as the change is recorded and treated as a controlled variable, so I
recorded it in the report and kept it identical across both arms.

My research question is narrower than the paper's. I wanted to know what happens to the cost of a run
and to the quality of the decision when one round of the bull and bear debate is removed.

The three figures at the bottom of the slide summarise the scope. Every number in this talk comes from
six full multi-agent runs, three for each arm, on one ticker and three dates, and I executed all of
them on this laptop in the last day.

## Slide 2 · What runs when you give it a ticker and a date (~90 s)

The diagram follows one run from left to right. The four analysts on the left cover the market, the
news, the fundamentals and social sentiment. They run in parallel, each keeps its own bounded tool
loop, and the debate starts only when every analyst has filed a report.

The orange box is the stage I modify. Bull and Bear argue, the research manager writes the investment
plan, the trader drafts a decision, three risk analysts argue the aggressive, neutral and conservative
cases, and the portfolio manager issues one of five ratings.

The two cards below explain why the course counts this as an agentic system. The analysts call real
data tools over several steps with a fixed budget, and every decision goes into a memory log. Five
trading days later the system fetches the realised return and the alpha against SPY, settles the
decision and writes a short reflection that the next run reads.

That settlement loop is the target I reproduced, and it is also the reason I did not try to match a
table from the paper.

## Slide 3 · Reproduction target (~75 s)

The repository makes a specific claim, quoted at the top of the slide: every cell is scored on
realized alpha against the instrument's regional benchmark and grouped by rating. A cell here means
one ticker on one date.

The timeline shows how a cell is measured. The run reads the analysis date, settlement enters at the
first close after that date so that no later information leaks in, and the outcome is measured over
the next five trading days.

Three definitions sit under the timeline. The raw return is the percentage change of the instrument
over the window. Alpha subtracts the SPY return over the same window. The hit rate asks whether the
rating pointed the right way, so Buy and Overweight expect positive alpha, Underweight and Sell expect
negative alpha, and Hold claims no direction and stays out of the hit rate.

The grey strip at the bottom marks what is outside this study. The paper reports annualised return,
Sharpe ratio and drawdown over a year and several tickers, and a two-day budget on a laptop with a
hosted API cannot support that. I reproduced the mechanism and its per-decision measurement, and the
report states that plainly.

## Slide 4 · Experimental setup (~80 s)

On the left, the table lists the configuration of both arms. Both arms come from a single function in
my harness, and the only difference is the first row, max_debate_rounds, which is 1 in the baseline,
the repository default, and 0 in the modified arm. The model, the temperature, the analysts, the
ticker, the dates and the tool budget are identical.

On the right I show what that integer does, because I read the routing code instead of trusting the
parameter name. The router ends the debate when the turn count reaches twice max_debate_rounds. With a
value of 1 the sequence is a Bull turn, a Bear turn and a hand-over to the research manager. With a
value of 0 the condition is already satisfied after the first Bull turn, so the Bear never speaks.

The first Bull turn stays unconditional because the graph wires the analysts into the Bull node. A
value of 0 therefore removes the rebuttal and still produces one Bull statement. A diff of the
configuration alone would not reveal that behaviour, and it matters for how the results are read.

## Slide 5 · Baseline results (~70 s)

The baseline produced three cells, all of them settled, with no pending entry left behind. The three
figures at the top give the totals: 61 LLM calls, 16 minutes of elapsed time, and a mean alpha of
plus 0.9 percent.

The table lists the cells. The ratings were Hold on 6 October, Underweight on 13 October and Hold on
20 October. The alpha was plus 2.8 percent, minus 0.2 percent and plus 0.1 percent, as the chart on
the right shows. Each cell took between 19 and 21 calls.

The reproduction target is therefore met in an honest but limited sense. The pipeline runs end to end,
every decision is logged, settled and scored, and the summary comes from my own log.

One pattern is worth noting. Two of the three ratings are Hold, and a Hold claims no direction, so the
baseline made a directional call in only one cell out of three.

## Slide 6 · Modification and comparison (~95 s)

The comparison covers cost and decisions. The three figures at the top give the cost. The modified arm
needed 260 seconds per cell against 321, which is 19 percent less time, 13 percent fewer calls and 18
percent fewer tokens. The chart shows the saving on every date. It is mechanical, because one fewer
analyst turn per cell would produce the same saving on other dates.

The grid on the right shows the decisions. Alpha is identical in both arms on every date, and that
follows from how the metric is defined. Alpha measures the instrument's realised excess return after
the date, so it belongs to the cell. What changes across arms is the rating and whether that rating
called the realised alpha correctly.

The baseline returned Hold twice and one correct Underweight. With the rebuttal removed, the modified
arm claimed Overweight in all three cells and was right twice, wrong once on 13 October.

The shorter debate did not add foresight. It removed the abstention, which is a real effect of a
one-integer change that a comparison of returns alone would not reveal.

## Slide 7 · Conclusions (~75 s)

The left column lists three findings that hold up. The mechanism reproduces, since a pinned commit and
pinned dependencies produce settled cells. The cost effect reproduces and is mechanical. The parameter
also behaves differently from what its name suggests, because zero rounds still gives one Bull turn.

The middle column lists three things that do not hold up. The paper's returns do not reproduce,
because the model and the dates differ and the metric is a per-decision alpha with no portfolio
backtest. Variance stays unmeasured, because three dates give three samples and every date ran once
in each arm, so part of the rating difference could be sampling noise. Decision quality in a portfolio
sense is also out of reach. I can show that the system committed more often and was right twice, and
I cannot show that it traded better.

The right column gives the next steps. The first change would be repeats on a single date before
adding further dates, because that separates an effect of the debate from model noise, and the present
design cannot answer that question.

The repository contains the harness, both configurations, every cell and every log, including a debug
diary with the eight blockers that cost time, such as the Schannel TLS failures, the pip resolver
backtracking, a sandboxed uv cache and an agent that looped on a macro tool without an API key.
Thank you for watching.
