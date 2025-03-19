
# from transformers import pipeline

# def classify_message(message):
#     # Define the categories for zero-shot classification
#     categories = ["greeting", "complaint", "question", "feedback"]

#     # Use the zero-shot-classification pipeline
#     classifier = pipeline("zero-shot-classification")
#     result = classifier(message, candidate_labels=categories)

#     # Return the predicted category
#     return result["labels"][0]  # Return the top predicted label
