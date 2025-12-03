<?php
<?php
// Do not display PHP errors to client — log them instead
ini_set('display_errors', '0');
ini_set('log_errors', '1');
error_reporting(E_ALL);

header('Content-Type: application/json; charset=utf-8');

$input = file_get_contents('php://input');
$data = json_decode($input, true);
if (!is_array($data)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid JSON']);
    exit;
}

$name    = trim($data['name'] ?? '');
$emailIn = trim($data['email'] ?? '');
$email   = filter_var($emailIn, FILTER_VALIDATE_EMAIL) ? $emailIn : '';
$phone   = trim($data['phone'] ?? '');
$city    = trim($data['city'] ?? '');
$comment = trim($data['comment'] ?? '');

// Set your real recipient here
$to = 'kazior.abay.91@example.com';
$subject = 'Новая заявка с сайта ScetchBox';
$body = "ФИО: $name\nEmail: $email\nТелефон: $phone\nГород: $city\nКомментарий: $comment\n";
$headers = "From: noreply@localhost\r\nReply-To: " . ($email ?: 'noreply@localhost') . "\r\nContent-Type: text/plain; charset=utf-8\r\n";

// Try to send mail (may be disabled on local env). Log result either way.
$mailOk = false;
if (function_exists('mail')) {
    $mailOk = @mail($to, $subject, $body, $headers);
}

$logLine = sprintf("[%s] mail_ok=%d to=%s name=%s email=%s phone=%s city=%s comment=%s\n",
    date('Y-m-d H:i:s'), (int)$mailOk, $to, $name, $email, $phone, $city, substr($comment,0,200));
file_put_contents(__DIR__ . '/send_email.log', $logLine, FILE_APPEND);

// Return JSON for client
echo json_encode(['success' => (bool)$mailOk, 'logged' => true]);
?>