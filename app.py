import streamlit as st
import pandas as pd

st.set_page_config(page_title="CSV Pivot Filter Tool", layout="wide")
st.title("CSV Pivot Filter Tool (Upgraded)")

uploaded = st.file_uploader("Upload a CSV", type=["csv"])

def flatten_columns(cols):
    """Flatten multi-index columns from pivot_table into nice strings."""
    if not isinstance(cols, pd.MultiIndex):
        return cols
    out = []
    for tup in cols:
        tup = [str(x) for x in tup if x not in (None, "", "nan")]
        out.append(" | ".join(tup))
    return out

if uploaded:
    df = pd.read_csv(uploaded)
    all_cols = df.columns.tolist()

    # Try to identify numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    st.subheader("1) Choose which columns become dropdown filters")
    filter_cols = st.multiselect("Filter columns (only these will show)", all_cols)

    # === MULTI-SELECT FILTERS ===
    st.subheader("2) Filter values (multi-select)")
    filtered_df = df.copy()

    for col in filter_cols:
        # Use strings for stable UI even if mixed types
        col_as_str = filtered_df[col].astype(str)

        unique_vals = sorted(col_as_str.dropna().unique().tolist())
        default_vals = unique_vals  # start as "All selected"

        selected = st.multiselect(
            f"{col}",
            options=unique_vals,
            default=default_vals,
            key=f"filter_{col}"
        )

        # If user deselects everything, show no rows
        if len(selected) == 0:
            filtered_df = filtered_df.iloc[0:0]
            break

        filtered_df = filtered_df[col_as_str.isin(selected)]

    st.divider()

    # === PIVOT BUILDER (Rows / Columns / Values) ===
    st.subheader("3) Pivot builder (Rows / Columns / Values)")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

    with c1:
        pivot_rows = st.multiselect("Rows (group by)", all_cols, key="rows")

    with c2:
        pivot_cols = st.multiselect("Columns (spread across)", all_cols, key="cols")

    with c3:
        # default to numeric columns if available
        default_values = numeric_cols[:1] if numeric_cols else []
        pivot_values = st.multiselect(
            "Values (what to summarize)",
            all_cols,
            default=default_values,
            key="values"
        )

    with c4:
        aggfunc = st.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], key="agg")

    st.caption("Tip: If you choose Columns, the result will look more like an Excel pivot (wide table).")

    # Build pivot-like table
    if pivot_rows or pivot_cols:
        working = filtered_df.copy()

        # If agg isn't count, try to coerce selected values to numeric
        if aggfunc != "count" and pivot_values:
            for v in pivot_values:
                working[v] = pd.to_numeric(working[v], errors="coerce")

        # If user chose no values:
        # - for count, we can count rows via size
        # - otherwise, ask for values
        if not pivot_values:
            if aggfunc == "count":
                # Count rows per group
                if pivot_cols:
                    pivot = (
                        working.pivot_table(
                            index=pivot_rows if pivot_rows else None,
                            columns=pivot_cols,
                            values=working.columns[0],  # dummy, not used for size; but pivot_table needs values
                            aggfunc="count",
                            dropna=False
                        )
                    )
                else:
                    pivot = (
                        working.groupby(pivot_rows, dropna=False)
                               .size()
                               .reset_index(name="count")
                    )
            else:
                st.info("Pick at least one Values column (or switch Aggregation to count).")
                pivot = None
        else:
            pivot = working.pivot_table(
                index=pivot_rows if pivot_rows else None,
                columns=pivot_cols if pivot_cols else None,
                values=pivot_values,
                aggfunc=aggfunc,
                dropna=False
            )

        if pivot is not None:
            # Make it a normal table for display + download
            if isinstance(pivot, pd.DataFrame):
                pivot_out = pivot.reset_index()
                pivot_out.columns = flatten_columns(pivot_out.columns)
            else:
                pivot_out = pivot.reset_index(name="value")

            st.dataframe(pivot_out, use_container_width=True)

            st.download_button(
                "Download pivot as CSV",
                pivot_out.to_csv(index=False),
                file_name="pivot_output.csv",
                mime="text/csv"
            )
    else:
        st.info("Pick at least one Row or one Column to build the pivot.")

    st.divider()
    st.subheader("Filtered raw data preview")
    st.dataframe(filtered_df, use_container_width=True)
