# utils/charts.py
# Reusable Plotly chart functions — all branded with KC Current colours

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from utils.constants import COLORS

FONT = "Arial, sans-serif"

def _base_layout(title: str = "", height: int = 400) -> dict:
    return dict(
        title       = dict(text=title, font=dict(family=FONT, size=18, color=COLORS["navy"], weight="bold")),
        height      = height,
        plot_bgcolor= "rgba(0,0,0,0)",
        paper_bgcolor= "rgba(0,0,0,0)",
        font        = dict(family=FONT, color="#333333"),
        margin      = dict(l=40, r=20, t=50, b=40),
        legend      = dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode   = "closest",
        hoverlabel  = dict(bgcolor="white", font_size=12, font_family=FONT),
        xaxis       = dict(showgrid=False, zeroline=False, linecolor="#E0E0E0", linewidth=1),
        yaxis       = dict(showgrid=True, gridcolor="#E0E0E0", zeroline=False, linecolor="#E0E0E0", linewidth=1)
    )


def standings_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart — NWSL standings by points."""
    colors = [COLORS["teal"] if kc else COLORS["navy"]
              for kc in df.get("is_kc", [False]*len(df))]
    fig = go.Figure(go.Bar(
        x          = df["points"],
        y          = df["team_name"],
        orientation= "h",
        marker_color= colors,
        text       = df["points"],
        textposition= "outside",
        hovertemplate= "<b>%{y}</b><br>Points: %{x}<extra></extra>",
    ))
    fig.update_layout(**_base_layout("NWSL Standings — Points", height=500))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11), title="")
    fig.update_xaxes(title="Total Points")
    return fig


def goals_bar(df: pd.DataFrame) -> go.Figure:
    """Grouped bar — Goals For vs Goals Against for top teams."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Goals For",     x=df["team_name"], y=df["goals_for"],
                         marker_color=COLORS["teal"]))
    fig.add_trace(go.Bar(name="Goals Against", x=df["team_name"], y=df["goals_against"],
                         marker_color=COLORS["gold"]))
    fig.update_layout(**_base_layout("Goals For vs Against", height=420), barmode="group")
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=10), title="")
    fig.update_yaxes(title="Goals")
    return fig


def results_timeline(df: pd.DataFrame) -> go.Figure:
    """Scatter — KC match results over the season with colour coding."""
    color_map = {"W": COLORS["win"], "D": COLORS["draw"], "L": COLORS["loss"]}
    df = df[df["result"].isin(["W","D","L"])].copy()
    df["color"] = df["result"].map(color_map)

    fig = go.Figure()
    for result, grp in df.groupby("result"):
        fig.add_trace(go.Scatter(
            x    = grp["date"],
            y    = grp["kc_goals"] - grp["opp_goals"],
            mode = "lines+markers",
            line = dict(dash="dot", width=1, color="grey"),
            name = {"W":"Win","D":"Draw","L":"Loss"}.get(result, result),
            marker= dict(color=color_map[result], size=14, line=dict(width=2, color="white")),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "%{customdata[1]} — %{customdata[2]}<br>"
                "GD: %{y}<extra></extra>"
            ),
            customdata=grp[["opponent","kc_goals","opp_goals"]].values,
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="grey", opacity=0.5)
    fig.update_layout(**_base_layout("KC Current — Match Goal Difference", height=380))
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Goal Difference")
    return fig


def xg_scatter(df: pd.DataFrame) -> go.Figure:
    """Scatter — xG vs Actual Goals, bubble = minutes played."""
    df = df[(df["goals"] > 0) | (df["xg"] > 0)].copy()
    max_min = df["minutes"].max() if "minutes" in df.columns else 90
    df["bubble"] = ((df.get("minutes", 90) / max_min) * 20 + 8).clip(8, 28)

    fig = go.Figure(go.Scatter(
        name = "Players",
        x    = df["xg"],
        y    = df["goals"],
        mode = "markers+text",
        text = df["player"],
        textposition= "top center",
        textfont= dict(size=10, color="#555"),
        marker= dict(
            size = df["bubble"],
            color= COLORS["teal"],
            opacity=0.8,
            line = dict(width=1, color="white"),
        ),
        hovertemplate= (
            "<b>%{text}</b><br>xG: %{x:.2f}<br>Goals: %{y}<br>Mins: %{customdata}<extra></extra>"
        ),
        customdata = df["minutes"]
    ))
    
    # Diagonal reference line (xG = Goals)
    mx = max(df["xg"].max(), df["goals"].max()) + 0.5
    fig.add_trace(go.Scatter(
        name = "xG = Goals",
        x=[0, mx], y=[0, mx], mode="lines",
        line=dict(dash="dash", color="grey", width=1.5),
        showlegend=True, hoverinfo="skip",
    ))
    
    fig.update_layout(**_base_layout("xG vs Actual Goals (Bubble Size = Minutes)", height=500))
    fig.update_xaxes(title="Expected Goals (xG)", showgrid=True)
    fig.update_yaxes(title="Actual Goals")
    return fig


def top_scorers_bar(df: pd.DataFrame, metric: str = "goals",
                    label: str = "Goals", n: int = 10) -> go.Figure:
    top = df.nlargest(n, metric)[["player", metric]].copy()
    fig = go.Figure(go.Bar(
        name        = label,
        x           = top[metric],
        y           = top["player"],
        orientation = "h",
        marker_color= COLORS["teal"],
        text        = top[metric],
        textposition= "outside",
        hovertemplate= "<b>%{y}</b><br>" + label + ": %{x}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(f"Top {n} {label}", height=420))
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(title=label)
    return fig


def season_trend_line(df: pd.DataFrame, y_col: str, title: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        name = title,
        x    = df["season"] if "season" in df.columns else df.index,
        y    = df[y_col],
        mode = "lines+markers",
        line = dict(color=COLORS["teal"], width=4, shape="spline"),
        marker= dict(size=10, color=COLORS["gold"], line=dict(color="white", width=2)),
        fill = "tozeroy",
        fillcolor = "rgba(0, 122, 138, 0.1)",
        hovertemplate= "%{x}: <b>%{y}</b><extra></extra>",
    ))
    fig.update_layout(**_base_layout(title, height=380))
    fig.update_xaxes(title="")
    fig.update_yaxes(title=title)
    return fig


def radar_chart(players: list, df: pd.DataFrame,
                metrics: list = None) -> go.Figure:
    """Radar/spider chart comparing up to 3 players."""
    if metrics is None:
        metrics = ["goals_p90", "assists_p90", "xg_p90", "pass_completion_pct", "defensive_actions"]
        
    metrics_present = [m for m in metrics if m in df.columns]
    if not metrics_present:
        return go.Figure()

    fig = go.Figure()
    palette = [COLORS["teal"], COLORS["gold"], COLORS["navy"]]

    for i, player in enumerate(players[:3]):
        row = df[df["player"] == player]
        if row.empty:
            continue
            
        # Normalize values slightly for radar vis (0-100 scale roughly)
        raw_vals = [float(row[m].iloc[0]) for m in metrics_present]
        max_vals = df[metrics_present].max().values
        norm_vals = [(v / m * 100) if m > 0 else 0 for v, m in zip(raw_vals, max_vals)]
        
        # close the polygon
        norm_vals += [norm_vals[0]]
        
        # Prettier metric names
        clean_metrics = [m.replace("_", " ").title() for m in metrics_present]
        clean_metrics += [clean_metrics[0]]

        fig.add_trace(go.Scatterpolar(
            r    = norm_vals,
            theta= clean_metrics,
            fill = "toself",
            name = player,
            line = dict(color=palette[i], width=2),
            marker = dict(size=8, color=palette[i]),
            opacity=0.7,
            hovertemplate="Player: " + player + "<br>%{theta}: <b>%{r:.1f}%</b> (of max)<extra></extra>"
        ))
        
    fig.update_layout(
        polar = dict(
            radialaxis=dict(visible=True, showticklabels=False, range=[0, 105], gridcolor="#E0E0E0"),
            angularaxis=dict(gridcolor="#E0E0E0", linecolor="#E0E0E0")
        ),
        **_base_layout("Player Comparison (Percentile of Max)", height=450),
    )
    return fig