import os
import time


UPLOAD_FOLDER = os.path.join(
    os.path.dirname(__file__),
    'uploads'
)


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


def save_file(request, field_name):

    file = request.files.get(field_name)

    if not file or file.filename == '':
        return None

    extension = os.path.splitext(file.filename)[1]

    filename = (
        str(int(time.time() * 1000))
        + '_'
        + field_name
        + extension
    )

    file.save(
        os.path.join(
            UPLOAD_FOLDER,
            filename
        )
    )

    return filename