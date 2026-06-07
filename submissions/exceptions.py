class SubmissionError(Exception):
    pass


class SessionExpiredError(SubmissionError):
    pass


class InvalidFileError(SubmissionError):
    pass


class StorageError(SubmissionError):
    pass