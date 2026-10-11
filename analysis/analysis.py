# %% [markdown]
# # Late deliveries and customer satisfaction - Olist
# Statistical analysis that backs up the SQL findings.
# Run top to bottom (VS Code / Jupyter treat `# %%` as cells), or:
#     python analysis/analysis.py
# Needs: data/olist.db and the order_delivery view (sql/03_delivery_analysis.sql).

# %%
import sqlite3
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from config import DB_PATH, FIG_DIR, REPORTS_DIR  # noqa: E402

FIG_DIR.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")
rng = np.random.default_rng(42)

# %% [markdown]
# ## 1. Load data

# %%
con = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM order_delivery", con)
con.close()
print(f"Delivered orders: {len(df):,}")
print(f"With a review score: {df.review_score.notna().sum():,}")
print(f"Late share: {df.is_late.mean():.1%}")

reviewed = df.dropna(subset=["review_score"]).copy()
reviewed["low_score"] = (reviewed.review_score <= 2).astype(int)

# %% [markdown]
# ## 2. Review score: late vs not late

# %%
summary = (reviewed.groupby("is_late")
           .agg(orders=("order_id", "count"),
                avg_score=("review_score", "mean"),
                pct_1_star=("review_score", lambda s: (s == 1).mean() * 100),
                pct_low_1_2=("low_score", "mean"))
           .round(3))
summary["pct_low_1_2"] *= 100
print(summary)
summary.to_csv(REPORTS_DIR / "score_late_vs_ontime.csv")

# %% [markdown]
# ## 3. Is the difference statistically real?
# Review scores are ordinal (1-5), so use Mann-Whitney U rather than a t-test,
# and report an effect size and a bootstrap confidence interval for the gap.

# %%
late = reviewed.loc[reviewed.is_late == 1, "review_score"].to_numpy()
ontime = reviewed.loc[reviewed.is_late == 0, "review_score"].to_numpy()

u_stat, p_mw = stats.mannwhitneyu(late, ontime, alternative="two-sided")
# Common-language effect size: P(random on-time score > random late score), ties = 0.5
cles = u_stat / (len(late) * len(ontime))
cles_ontime_higher = 1 - cles

diffs = [rng.choice(ontime, len(ontime)).mean() - rng.choice(late, len(late)).mean()
         for _ in range(2000)]
ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])

contingency = pd.crosstab(reviewed.is_late, reviewed.low_score)
chi2, p_chi, _, _ = stats.chi2_contingency(contingency)

print(f"Mean score  on-time: {ontime.mean():.2f}   late: {late.mean():.2f}")
print(f"Gap (on-time - late): {ontime.mean() - late.mean():.2f}  "
      f"95% bootstrap CI [{ci_low:.2f}, {ci_high:.2f}]")
print(f"Mann-Whitney U p-value: {p_mw:.2e}")
print(f"P(on-time score > late score): {cles_ontime_higher:.2f}")
print(f"Chi-square (late vs low score 1-2) p-value: {p_chi:.2e}")

pd.DataFrame({
    "metric": ["mean_ontime", "mean_late", "gap", "gap_ci_low", "gap_ci_high",
               "mannwhitney_p", "prob_ontime_higher", "chi2_low_score_p"],
    "value": [ontime.mean(), late.mean(), ontime.mean() - late.mean(), ci_low, ci_high,
              p_mw, cles_ontime_higher, p_chi],
}).to_csv(REPORTS_DIR / "stat_tests.csv", index=False)

# %% [markdown]
# ## 4. Score by delay bucket

# %%
bucket = (reviewed.groupby("delay_bucket")
          .agg(orders=("order_id", "count"),
               avg_score=("review_score", "mean"),
               pct_low=("low_score", "mean")))
bucket["pct_low"] *= 100
print(bucket.round(2))
bucket.to_csv(REPORTS_DIR / "score_by_delay_bucket.csv")

fig, ax = plt.subplots(figsize=(9, 4.5))
sns.barplot(x=bucket.index, y=bucket.avg_score, color="#4C78A8", ax=ax)
ax.set_xlabel("Delivery vs estimated date")
ax.set_ylabel("Average review score")
ax.set_ylim(1, 5)
ax.set_title("Average review score by delivery delay")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
fig.savefig(FIG_DIR / "score_by_delay_bucket.png", dpi=150)
if matplotlib.get_backend().lower() != "agg":
    plt.show()
plt.close(fig)

# %% [markdown]
# ## 5. Distribution of scores, late vs on-time

# %%
dist = (reviewed.groupby("is_late").review_score
        .value_counts(normalize=True).rename("share").reset_index())
dist["group"] = dist.is_late.map({0: "On time / early", 1: "Late"})

fig, ax = plt.subplots(figsize=(8, 4.5))
sns.barplot(data=dist, x="review_score", y="share", hue="group",
            palette=["#4C78A8", "#E45756"], ax=ax)
ax.set_xlabel("Review score")
ax.set_ylabel("Share of orders")
ax.set_title("Review score distribution: late vs on-time")
ax.legend(title="")
plt.tight_layout()
fig.savefig(FIG_DIR / "score_distribution.png", dpi=150)
if matplotlib.get_backend().lower() != "agg":
    plt.show()
plt.close(fig)

# %% [markdown]
# ## 6. Does lateness still matter after controlling for other factors?
# Logistic regression: probability of a low score (1-2) vs. lateness,
# order value and freight share. Odds ratio > 1 means higher odds of a low score.

# %%
con = sqlite3.connect(DB_PATH)
value = pd.read_sql_query(
    "SELECT order_id, SUM(price) AS items_value, SUM(freight_value) AS freight_value "
    "FROM order_items GROUP BY order_id", con)
con.close()

model_df = reviewed.merge(value, on="order_id", how="inner")
model_df = model_df[model_df.items_value > 0].copy()
model_df["freight_share"] = model_df.freight_value / model_df.items_value
model_df["log_value"] = np.log(model_df.items_value)
model_df["freight_share"] = model_df.freight_share.clip(upper=model_df.freight_share.quantile(0.99))

logit = smf.logit("low_score ~ is_late + log_value + freight_share + delivery_days",
                  data=model_df).fit(disp=False)
odds = pd.DataFrame({
    "odds_ratio": np.exp(logit.params),
    "ci_low": np.exp(logit.conf_int()[0]),
    "ci_high": np.exp(logit.conf_int()[1]),
    "p_value": logit.pvalues,
}).round(4)
print(odds)
odds.to_csv(REPORTS_DIR / "logit_odds_ratios.csv")

# %% [markdown]
# ## 7. Do customers whose first order was late come back less often?
# Same cut-off as the SQL: first order before 2018-01-01.

# %%
con = sqlite3.connect(DB_PATH)
orders = pd.read_sql_query(
    "SELECT customer_unique_id, order_purchase_timestamp, is_late FROM order_delivery", con)
con.close()

orders = orders.sort_values(["customer_unique_id", "order_purchase_timestamp"])
orders["rn"] = orders.groupby("customer_unique_id").cumcount() + 1
orders["n_orders"] = orders.groupby("customer_unique_id").order_purchase_timestamp.transform("size")
first = orders[(orders.rn == 1) & (orders.order_purchase_timestamp < "2018-01-01")].copy()
first["repeat"] = (first.n_orders > 1).astype(int)

rep = first.groupby("is_late").agg(customers=("repeat", "size"), repeat_rate=("repeat", "mean"))
rep["repeat_rate"] *= 100
print(rep.round(2))
rep.to_csv(REPORTS_DIR / "repeat_by_first_order_late.csv")

table = pd.crosstab(first.is_late, first["repeat"])
chi2_r, p_r, _, _ = stats.chi2_contingency(table)
print(f"Chi-square p-value (first order late vs repeat): {p_r:.3g}")

# %% [markdown]
# ## 8. What to write in the README
# Copy the numbers from the printed tables / reports/*.csv. Report what the data
# shows, including the case where the effect is small or the repeat-rate gap is
# not significant. Mention caveats: this is observational data (correlation, not
# proof of cause), only customers who left a review are included, and repeat
# purchasing is rare so confidence intervals can be wide.
