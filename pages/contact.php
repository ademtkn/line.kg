<?php

// Only process POST requests.
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Get the form fields and remove whitespace.
    $name = strip_tags(trim($_POST["name"]));
    $name = str_replace(array("\r", "\n"), array(" ", " "), $name);
    $message = strip_tags(trim($_POST["message"]));
    $email = filter_var(trim($_POST["email"]), FILTER_SANITIZE_EMAIL);

    // Check that all required data was sent to the mailer.
    if (empty($name) || empty($message) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
        // Set a 400 (bad request) response code and return JSON response.
        http_response_code(400);
        echo json_encode(["status" => "error", "message" => "Please complete the form and try again."]);
        exit;
    }

    // Set the recipient email address.
    $recipient = "mizansorker@gmail.com";

    // Set the email subject.
    $subject = "New Message from $name";

    // Build the email content.
    $email_content = "Name: $name\n";
    $email_content .= "Email: $email\n\n";
    $email_content .= "Message:\n$message\n";

    // Build the email headers.
    $email_headers = "From: $name <$email>\r\n";
    $email_headers .= "Reply-To: $email\r\n";

    // Send the email.
    if (mail($recipient, $subject, $email_content, $email_headers)) {
        // Set a 200 (okay) response code and return JSON response.
        http_response_code(200);
        echo json_encode(["status" => "success", "message" => "Thank You! Your message has been sent."]);
    } else {
        // Set a 500 (internal server error) response code and return JSON response.
        http_response_code(500);
        echo json_encode(["status" => "error", "message" => "Oops! Something went wrong and we couldn't send your message."]);
    }

} else {
    // Not a POST request, set a 403 (forbidden) response code and return JSON response.
    http_response_code(403);
    echo json_encode(["status" => "error", "message" => "There was a problem with your submission, please try again."]);
}

?>
