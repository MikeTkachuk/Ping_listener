# Ping_listener
A backend that sends emails in case ping is not received within the specified time

## Server config template
Frequency is refered to as a delay in seconds between processing loops.

  {  
  'server_root':(str) 'https://example.net' a string to append to logs link in the emails,  
  'base_frequency': (scalar>=0) a delay between the steps of a ping absence listener,  
  'email_processing_frequency': (scalar>=0) a delay before the next processing of the emails queue,  
  'recipient': (str or list(str)) representing the recipient email or list of emails,  
  'users': a dict of pairs (username:(unique str),user config described below)  
  }

### User config template
  {  
  'monitor': (bool) if false never sends emails,  
  'max_sleep': (scalar>=0) max delay between pings in seconds,  
  'device_email': (str or list(str)) Optional. Represents a device-specific email or list of emails.  
		Defaults to the 'recipient' field of a server config,
  'email_frequency': (scalar>=0) min delay between subsequent emails for a particular user  
  }
  
 
 ## Required environment variables
 * TESTING_PASSWORD - (str) secures testing mode accessible via <server>/. Its absence  
                      raises an exception only if an attempt to access the testing interface is made  
                      but is likely to crash an application.
  
 * SMTP_PORT - (int) defaults to 465
 * SMTP_LOGIN - (str) an email/login of the application
 * SMTP_PASSWORD - (str) a password to access SMTP API. 
  
  The email sending is performed via SMTP SSL.
 
__________
 
 # Requests
 ### Ping
  A ping should be made at <server>/ping via GET request  
  **Args**:  
* username - unique username on behalf of whom a ping is made.  
  
**Returns**:  
    (str) datetime formated as '%y/%m/%d %H:%M:%S'.  
    For more info about the notation see https://docs.python.org/3/library/datetime.html?highlight=strf#strftime-strptime-behavior
 ### Logs
  A ping should be made at <server>/logs via GET request  
  **Args**:  
* username - unique username on behalf of whom a ping is made.
* year \ 
* month - double digit format
* day  /  
  
**Returns**:  
    A list of strings of format '%H:%M:%S',  where each entry is the  
    time of a ping for a particular user on the specified date.
