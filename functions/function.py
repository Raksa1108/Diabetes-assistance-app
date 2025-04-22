import altair as alt
import pandas as pd

def make_donut(percent, label='Prediction', input_color='blue'):
    """
    Creates a donut chart to visualize the diabetes risk percentage.
    
    Parameters:
    - percent: float (percentage value)
    - label: str (center label of the donut)
    - input_color: str (color of the filled portion of the donut)
    
    Returns:
    - alt.Chart object (donut chart)
    """

    source = pd.DataFrame({
        "Category": [label, "Remaining"],
        "Value": [percent, 100 - percent]
    })

    chart = alt.Chart(source).mark_arc(innerRadius=50, outerRadius=70).encode(
        theta=alt.Theta(field="Value", type="quantitative"),
        color=alt.Color(
            "Category:N",
            scale=alt.Scale(domain=[label, "Remaining"],
                            range=[input_color, "#f5b5d9"]),  # pink transparent for unfilled
            legend=None
        )
    ).properties(width=300, height=300)

    text = alt.Chart(pd.DataFrame({
        'text': [f"{percent:.1f}%"]
    })).mark_text(
        fontSize=28,
        font='Arial',
        fontWeight='bold',
        color='black'
    ).encode(
        text='text:N'
    ).properties(width=300, height=300)

    return chart + text
