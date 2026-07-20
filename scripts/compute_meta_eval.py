"""Meta-eval step 2: run this AFTER you've filled in the human_passed
column in reports/labels_to_fill.csv by hand.

Usage: python scripts/compute_meta_eval.py
"""

from app.services.meta_eval import compute_agreement, load_labels, load_results


def main() -> None:
    results = load_results("reports/meta_eval_results.json")
    labels = load_labels("reports/labels_to_fill.csv")

    summary = compute_agreement(results, labels)
    print("Judge vs. human agreement:\n")
    print(summary.to_string(index=False))

    print(
        "\nRule of thumb for reading Cohen's kappa: <0.2 slight, 0.2-0.4 fair, "
        "0.4-0.6 moderate, 0.6-0.8 substantial, >0.8 near-perfect agreement."
    )


if __name__ == "__main__":
    main()
