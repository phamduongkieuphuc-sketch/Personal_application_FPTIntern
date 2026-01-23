from transformers import ViltProcessor, ViltForQuestionAnswering
from PIL import Image
import torch
import numpy

image = Image.open("/home/william-pham/Pictures/Screenshots/hoa_don.png")
img_np = numpy.array(image)[:,:,:3]
image = Image.fromarray(img_np)
print(img_np.shape)

processor = ViltProcessor.from_pretrained("dandelin/vilt-b32-finetuned-vqa")
model = ViltForQuestionAnswering.from_pretrained("dandelin/vilt-b32-finetuned-vqa")

question = "What is the title of the document?"

encoding = processor(image, question, return_tensors="pt")
outputs = model(**encoding)

logits = outputs.logits
answer_id = logits.argmax(-1).item()
print(f"question:", question)
print(model.config.id2label[answer_id])
