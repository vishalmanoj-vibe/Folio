import plotly.graph_objects as go

from components.charts.helpers import apply_standard_layout, create_empty_fig


def build_holdings_bubble_chart(blended_data: dict, theme_tokens: dict) -> go.Figure:
    """
    Creates a bubble chart of top underlying company holdings.
    """
    if not blended_data:
        return create_empty_fig("No data available", 600, theme_tokens)

    # Top 50 items
    top_items = list(blended_data.items())[:50]

    companies = []
    weights = []
    texts = []

    for comp, data in top_items:
        w = data["weight"]
        companies.append(comp)
        weights.append(w)

        sources = data.get("sources", {})
        source_str = "<br>".join([f"{k}: {v}%" for k, v in sources.items()])

        texts.append(f"<b>{comp}</b><br>Total Exposure: {w}%<br><br>Sources:<br>{source_str}")

    fig = go.Figure()

    max_w = max(weights) if weights else 1

    fig.add_trace(
        go.Scatter(
            x=companies,
            y=weights,
            mode="markers",
            marker=dict(
                size=weights,
                sizemode="area",
                sizeref=2.0 * max_w / (80.0**2),  # Target max size ~80px
                sizemin=4,
                color=weights,
                colorscale="Teal",
                showscale=False,
                line=dict(width=1, color=theme_tokens.get("bg", "#000")),
            ),
            text=companies,
            hovertext=texts,
            hoverinfo="text",
        )
    )

    fig = apply_standard_layout(fig, theme_tokens)
    fig.update_layout(
        height=600,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
        yaxis=dict(
            showgrid=True,
            zeroline=False,
            title="Blended Weight (%)",
            gridcolor=theme_tokens.get("border", "#333"),
        ),
        margin=dict(l=40, r=20, t=20, b=20),
    )

    return fig
