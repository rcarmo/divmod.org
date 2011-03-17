
Divmod Quotient
===============

Divmod Quotient is a messaging platform developed as an Offering for Divmod
Mantissa.

It is currently in the very early stages of development, but you can already
use it to read your mail.

(Divmod, Inc. is planning to offer a commercial service based on Quotient in
the near future.  Watch http://divmod.org/ for an announcement!)


Dependencies
------------

Quotient is an offering for Divmod Mantissa. It depends on SpamBayes 1.0 and
Divmod Mantissa. See DEPS.txt in the Mantissa release for more information on
Mantissa dependencies.


Quick Start
-----------

Want to experiment with Quotient? Here's how to quickly get it up and running.
Note that a Quotient configured in this manner is not suitable for use in
production.


1. Launch an instance of Mantissa

Run the following commands:

    $ axiomatic -d mantissa.axiom mantissa
    Enter Divmod Mantissa password for 'admin@localhost': 
    Confirm Divmod Mantissa password for 'admin@localhost': 
    ...
    $ axiomatic -d mantissa.axiom start

`axiomatic` will prompt you for a password for `admin`. It will also dump some
information about SSL certificates.


2. Install the Quotient Offering

 * Browse to http://localhost:8080/private 
 * Login as admin@localhost, providing the password you gave in Step 1.
 * Click on the "Quotient" offering. The red border should turn yellow, then
   green.


3. Create a Quotient product

  * Mouse over the Admin tab in the top-left corner, a menu should drop
    down.
  * Click the Products menu item
  * Check all of the Quotient powerups which look interesting (or just check
    them all)
  * Click the "Installable Powerups" button at the bottom to create a
    product with these powerups


4. Create a Quotient signup

This allows users to sign up for accounts on your Mantissa server and have
access to the Quotient offering.

 * Mouse over the Admin tab again
 * Click the Signups menu item
 * Select the product created in step 3
 * Select the "Required User Information" signup type
 * Click the "Create Signup" button.


5. Sign up for a Quotient-enabled account

 * Logout of the admin@localhost account
 * Sign up as a new user
 * Log in as the new user


Note that you *must* point your browser to "localhost".  This is because you
created a user "admin@localhost", from which Mantissa derived the fact that
"localhost" is a domain which it is responsible for.  Signup is only allowed
for domains Mantissa believes itself to be responsible.

You should see Quotient running in your browser. 
