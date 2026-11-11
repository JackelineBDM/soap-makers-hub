"""Forms for writing and editing reviews."""
from django import forms

from .models import Review

RATING_CHOICES = [(5, "5 - Excellent"), (4, "4 - Good"), (3, "3 - Okay"),
                  (2, "2 - Poor"), (1, "1 - Bad")]


class ReviewForm(forms.ModelForm):
    """Rating from 1 to 5 and a comment of at least 10 characters."""

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES, coerce=int,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "comment": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }

    def clean_comment(self):
        """Reject comments that are too short once spaces are removed."""
        comment = self.cleaned_data["comment"].strip()
        if len(comment) < 10:
            raise forms.ValidationError(
                "Please write at least 10 characters."
            )
        return comment
