from google.cloud import storage
import base64

from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict
from PIL import Image

_ALLOWED_EXTENSIONS = {'jpg', 'jpeg', "webp"}


def allowed_file(filename):
    """Checks if uploaded file contains one of the allowed extensions."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in _ALLOWED_EXTENSIONS


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to a Google Cloud Bucket """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    generation_match_precondition = 0
    blob.upload_from_filename(
        source_file_name, if_generation_match=generation_match_precondition)


def create_thumbnail(image_name):
    """Creates a thumbnail of an image"""
    image = Image.open(image_name)
    image.thumbnail((90, 90))
    saved_img_name = "/tmp/thumb.png"
    image.save(saved_img_name)
    return saved_img_name


def predict_image_classification_sample(
    filename: str,
    project: str = "1026343004976",
    endpoint_id: str = "1473251023219851264",
    location: str = "us-central1",
    api_endpoint: str = "us-central1-aiplatform.googleapis.com",
):
    """"Returns a prediction if contains a bedbug."""
    # The AI Platform services require regional API endpoints.
    client_options = {"api_endpoint": api_endpoint}
    # Initialize client that will be used to create and send requests.
    # This client only needs to be created once, and can be reused for multiple requests.
    client = aiplatform.gapic.PredictionServiceClient(
        client_options=client_options)
    with open(filename, "rb") as f:
        file_content = f.read()

    # The format of each instance should conform to the deployed model's prediction input schema.
    encoded_content = base64.b64encode(file_content).decode("utf-8")
    instance = predict.instance.ImageClassificationPredictionInstance(
        content=encoded_content,
    ).to_value()
    instances = [instance]
    # See gs://google-cloud-aiplatform/schema/predict/params/image_classification_1.0.0.yaml for the format of the parameters.
    parameters = predict.params.ImageClassificationPredictionParams(
        confidence_threshold=0.5,
        max_predictions=5,
    ).to_value()
    endpoint = client.endpoint_path(
        project=project, location=location, endpoint=endpoint_id
    )
    response = client.predict(
        endpoint=endpoint, instances=instances, parameters=parameters
    )
    print("response")
    print(" deployed_model_id:", response.deployed_model_id)
    # See gs://google-cloud-aiplatform/schema/predict/prediction/image_classification_1.0.0.yaml for the format of the predictions.
    predictions = response.predictions

    confidence = predictions[0]['confidences'][0]
    bedbug_classification = True if predictions[0]['displayNames'][0] == "Bedbug" else False

    final_result = {"confidence": confidence,
                    "raw_name": predictions[0]['displayNames'], "classification":  bedbug_classification}
    print(final_result)
    return final_result
