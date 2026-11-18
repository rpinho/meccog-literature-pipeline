You are reading ONE scientific figure to fill in statistics for rows extracted from the same paper. Look at the image carefully. Never guess: a value you cannot see stays as it is.

Figure legend (from the paper):
{legend}

Rows that cite this figure (numbered by "item"):
{rows}

For EACH row, look at the panel its data_location names and return:
- "effect_size": the size of the change for the row's comparison, in one of these shapes only: "40%" (percent change, no sign), "2.5x" (fold, ratio of the two groups), "dpH=0.6" (a named difference, letters=number), "qualitative", or "N/A".
    * If the group values are PRINTED on the figure (numbers on or above the bars), use them: give the difference or ratio, and put both printed values in "note". Provenance "printed_on_figure".
    * Else, if you can measure it from bar heights or point positions against the axis, write it with a leading ~ (e.g. "~40%", "~2.1x") and provenance "estimated_from_figure". Read the axis carefully, including where it starts (axes that do not start at 0 change percentages).
    * Else keep the row's current value and provenance.
- "p_value": ONLY from significance marks on this panel interpreted with THIS legend's own key (e.g. legend says ** p < 0.01 and the panel shows ** over this comparison -> "<0.01"), provenance "visual_only". "ns" with a legend that defines it (e.g. ns, p > 0.05) -> ">0.05". If the legend has no key, or the marks are unclear, keep the row's current value. Never estimate a P value from the data.
- "sample_size": the number of plotted points per group if the points are clearly visible and countable, with a leading ~ (e.g. "~6"), provenance "estimated_from_figure"; give a range "~5-7" if groups differ. Else keep the row's current value.
- "panel_ok": true if the panel the row names shows the comparison the row describes, else false.
- "note": at most 25 words: what you read and where (e.g. "bars labelled 4.08 and 5.20; *** above").

Return ONLY a JSON array, one object per row, in the same order:
[{{"item": 1, "effect_size": "...", "effect_size_provenance": "...", "p_value": "...", "p_value_provenance": "...", "sample_size": "...", "sample_size_provenance": "...", "panel_ok": true, "note": "..."}}]
