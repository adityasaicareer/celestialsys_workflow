# Visitor Management Application

## Functional & Technical Requirements Specification

*Prepared from application walkthrough session conducted by Narendra*  
*Session: NextGen Alpha — Meeting Recording, 22 July 2026*

> **Transcription note:** This Markdown specification retains the source document's section order, requirements, tables, and figure captions. The **Technical Considerations** subsection consolidates statements already present in the source; it introduces no new requirement. Source screenshots are represented below by text descriptions.

## Table of Contents

1. [Application Overview](#1-application-overview)
2. [User Roles and Permissions](#2-user-roles-and-permissions)
3. [Dashboard Module](#3-dashboard-module)
4. [Visitor Entry Module](#4-visitor-entry-module)
5. [Approval Workflow Module](#5-approval-workflow-module)
6. [User Management Module](#6-user-management-module)
7. [Reports Module](#7-reports-module)
8. [Location, Access Card, and Device Certificate Handling](#8-location-access-card-and-device-certificate-handling)
9. [Consolidated Business Rules](#9-consolidated-business-rules)
10. [Enhancements and Follow-Up Action Items](#10-enhancements-and-follow-up-action-items)
11. [Glossary](#11-glossary)

## 1. Application Overview

The Visitor Management Application is a web-based system designed to digitize and standardize the process of registering, approving, and tracking visitors across an organization's office locations. The application currently supports three office locations — WTC, Jayanagar, and Noida — and provides a centralized dashboard for monitoring visitor activity across all sites.

The system is built around a role-based access model, an approval-driven visitor workflow, and reporting capabilities that allow administrators to analyze visitor trends and export data for record-keeping or compliance purposes.

### 1.1 Purpose

- Replace manual, register-based visitor logging with a digital, auditable workflow.
- Enforce an approval step before any visitor is granted entry.
- Provide administrators with visibility and reporting across multiple office locations.
- Maintain a controlled, traceable record of who created, approved, rejected, or deleted each record.

### 1.2 Supported Locations

- WTC
- Jayanagar
- Noida

## 2. User Roles and Permissions

The application defines three distinct user roles, each with a specific scope of permissions. Access to features and data is controlled entirely by the role assigned to a user account.

| Role | Key Permissions | Typical User |
| --- | --- | --- |
| Super Admin | Approve new user registrations; assign/change user roles; manage organizations; add, edit, and delete (soft delete) users; full access to all modules | System owner / IT administrator |
| Admin | Approve or reject visitor entries; generate and export reports; view dashboard | Office / facility manager |
| User | Create (enter) visitor details, including capturing visitor photo; cannot edit or delete own submitted entries; cannot reset own password | Security staff at reception |

### 2.1 Role-Based Restrictions

- Users (security staff) cannot edit their own profile details or reset their own password — this requires Super Admin intervention.
- Users cannot edit a visitor entry once it has been submitted. If details are incorrect, a new visitor application/entry must be submitted.
- Admins and Super Admins can edit visitor entries to correct incorrect information, and can approve or reject entries.
- Only a Super Admin can approve new user registrations and assign roles.

## 3. Dashboard Module

The dashboard is the landing screen of the application and gives users an at-a-glance view of visitor activity.

**Screen description:** The screenshot shows the **Create Visitor** page. It contains fields for phone number, email, first name, last name, pass type, origin, whom to meet, approver, date and time, location, multi-day selection, duration, and visitor consent. A capture/upload area is available for the visitor image, with **Cancel** and **Save** actions. The left navigation includes Dashboard, Users, Approvals, Reports, Create Visitor, Setting, and Logout.

*Figure 1: Dashboard view listing visitors across office locations.*

### 3.1 Functionality

- Displays a consolidated list of all visitors who have visited any of the three office locations (WTC, Jayanagar, Noida).
- Access to the dashboard and the data visible within it is governed by the logged-in user's role.
- Used primarily to monitor ongoing and historical visitor activity.

### 3.2 Planned Enhancements

- Add charts/graphs showing top visitors, recent activity, and month-wise visitor statistics.
- Add quick-approve buttons directly on the dashboard for pending approvals, reducing the need to navigate to the Approvals screen.

## 4. Visitor Entry Module

This module is used primarily by security staff (the "User" role) to register a new visitor at the point of entry.

**Screen description:** The screenshot shows the **Reports** page. It provides From date and To date filters, filter and download controls, and a paginated visitor-results table. Visible columns include Sl No, Badge Id, Visitor Name, Visitee, Coming From, Visit Status, Visit Date, and Check In.

*Figure 2: Visitor entry form used to capture new visitor details.*

### 4.1 Visitor Entry Workflow

1. Security staff selects the option to create a new visitor entry.
2. A photo of the visitor is captured using the in-app camera option.
3. Required details are entered: visitor name, pass type, location, and the approver responsible for approving the visit.
4. The application supports multiple pass types and visit durations, selectable at the time of entry.
5. Location can be selected manually, or auto-filled based on the device's current location (restricted to the three supported office locations).
6. If applicable, the visitor's access card assignment and device certificate details are captured for security and IT provisioning purposes.
7. If the visitor requires internet access, this is flagged as part of the entry so that the responsible admin is notified.
8. The entry is submitted and enters the approval queue as "Waiting for Approval."

### 4.2 Field-Level Notes

- **Photo capture:** mandatory for every visitor entry, taken via camera (not file upload).
- **Pass type & duration:** configurable per visit; supports multiple types.
- **Approver selection:** the staff member selects who the entry should be routed to for approval.
- **Access card & device certificates:** optional fields captured when a visitor requires physical/IT access provisioning.

### 4.3 Editing Rules

- Once submitted, a User cannot edit their own visitor entry.
- If incorrect information was entered, the visitor (or security staff) must submit a new application/entry.
- Admins and Super Admins retain the ability to edit an existing visitor entry to correct errors.

## 5. Approval Workflow Module

**Screen description:** The screenshot shows the lower portion of the **Create Visitor** page. It displays the duration list (including 1:00, 2:00, 3:00, Half-Day, and Full-Day), optional device or gadget details, access-card details, check-out time, ID-proof type and number, an Internet Needed option, visitor consent, and Save/Cancel controls.

*Figure 3: Approvals view segregating visitor entries by status.*

### 5.1 Approval States

| Status | Description |
| --- | --- |
| Waiting for Approval | Newly created visitor entries that have not yet been reviewed by an Admin/Super Admin. |
| Approved | Entries reviewed and approved; the visitor is permitted entry. |
| Rejected | Entries reviewed and rejected; the visitor is not permitted entry. |

### 5.2 Approval Rules

- Only Admins and Super Admins can approve or reject a visitor entry.
- Only approved visitors are permitted entry to the office.
- A rejected entry cannot subsequently be re-approved directly; however, the entry can be edited (by an Admin/Super Admin) and resubmitted for review.
- A free-text field is available to capture the reason for rejection. This field is optional (not mandatory) at present.

## 6. User Management Module

**Screen description:** The screenshot shows another view of the **Create Visitor** page, with a multi-day visit selected. It includes a date-based duration field, an in-app visitor photo area, device or gadget details, access-card information, check-out time, ID-proof type and number, Internet Needed, visitor consent, and Save/Cancel controls.

*Figure 4: User management screen for adding, editing, and deleting user accounts.*

### 6.1 User Registration and Approval

1. A new user registers for an account within the application.
2. The registration remains inactive until a Super Admin reviews and approves it.
3. Once approved, the user is granted access and can log in.

### 6.2 Role Assignment

- Roles (Super Admin, Admin, User) are assigned at the time a user is created.
- Super Admins can add new users and edit existing users' details and roles.
- Admins are limited to approving/rejecting visitors and generating reports — they cannot manage other users.

### 6.3 Deleting Users — Soft Delete

Deleting a user in the application performs a soft delete rather than a permanent removal.

- The user record remains in the database but is flagged as deleted.
- This preserves an audit trail, including which Super Admin performed the deletion.
- Soft deletion prevents permanent loss of historical data associated with the user.

### 6.4 Password Reset

- A password reset is initiated by sending a reset link to the user's registered email address.
- The user follows the link to set a new password securely.
- Email/SMS integration is not yet implemented; this is planned as a future enhancement using a free/low-cost email service.
- Users cannot reset their own password directly without a Super Admin-initiated flow.

## 7. Reports Module

**Screen description:** The screenshot shows the **Users** management page. It has a search field, an add-user button, and a table of user accounts with ID, first name, last name, email, role, organisation, and actions. The actions shown include edit, delete, and password-reset controls.

*Figure 5: Reports screen with filter and export options.*

### 7.1 Filtering

- Reports can be filtered by date range.
- Reports can be filtered by user (the staff member who created the entry, or the approver).
- Status-based filtering (approved / rejected / pending) is supported for analysis.

### 7.2 Export

- Report data can be exported/downloaded in Excel format.
- Report data can be exported/downloaded in PDF format.

### 7.3 Navigation

- Pagination is implemented on the reports list for easier navigation through large volumes of visitor records.

## 8. Location, Access Card, and Device Certificate Handling

### 8.1 Location Autofill

The application is designed to pre-fill the location field on the visitor entry form based on the device's current location. Auto-detected locations are restricted to the three supported offices (WTC, Jayanagar, Noida), reducing manual data-entry errors and ensuring the visitor is logged against the correct site.

### 8.2 Access Cards and Device Certificates

Where a visitor requires physical building access or needs to connect a device to office infrastructure, the following are captured at the time of entry:

- Access card assignment details.
- Device certificate information, where applicable.

These fields support downstream security and IT provisioning workflows.

### 8.3 Internet Access Requests

When a visitor requires internet access, this need is captured on the visitor entry form. The current (as-is) workflow is:

1. The request for internet access is flagged during visitor entry.
2. The responsible Admin is notified of the request.
3. The Admin coordinates with the IT team to arrange the necessary credentials.

> **Note:** The application currently captures the request but does not automate the credential-provisioning step itself — this remains a manual, IT-team-driven process.

### 8.4 Configurable Notifications

- Admins can be notified when a visitor requests internet access.
- Notification preferences are configurable — Admins can mute or adjust notifications according to preference.
- This is intended to keep Admins aware of special access needs without overwhelming them with alerts.

### 8.5 Technical Considerations

- The application is web-based and uses role-based access to control modules and data visibility.
- Visitor photos are captured through the in-app camera rather than a file upload.
- Device location may be used to pre-fill the office location, limited to WTC, Jayanagar, and Noida.
- User deletion uses a database soft-delete pattern to preserve historical data and an audit trail.
- Reports support Excel and PDF exports, and pagination supports large record volumes.
- Password-reset email/SMS integration and automated IT credential provisioning are not yet implemented.

## 9. Consolidated Business Rules

| # | Rule |
| --- | --- |
| 1 | Only approved visitors are permitted entry. |
| 2 | Users can create visitor entries but cannot edit them after submission; corrections require a new entry. |
| 3 | Admins/Super Admins can edit visitor entries to fix incorrect data. |
| 4 | A rejected visitor entry cannot be re-approved directly; it can be edited and resubmitted for review. |
| 5 | Rejection reason is captured via free text but is optional, not mandatory. |
| 6 | New user accounts require Super Admin approval before login is permitted. |
| 7 | User deletion is a soft delete — records are flagged, not physically removed. |
| 8 | Users cannot edit their own profile or reset their own password without Super Admin involvement. |
| 9 | Password resets are handled via an emailed reset link (email/SMS integration pending). |
| 10 | Location autofill is restricted to the three supported offices: WTC, Jayanagar, Noida. |

## 10. Enhancements and Follow-Up Action Items

The following enhancements and open action items were identified during the walkthrough session. All items are currently owned by Narendra.

| Action Item | Description | Owner |
| --- | --- | --- |
| User edit permissions | Verify whether users can currently edit their own submitted visitor information on the dashboard; update the system if this capability needs to be added or restricted. | Narendra |
| Location autofill | Implement default location selection based on the user's current device location, limited to the three specified office locations. | Narendra |
| Internet access notifications | Plan and implement a notification system to alert admins when a visitor requests internet access, with configurable notification settings. | Narendra |
| Email integration for password reset | Research and integrate a free/low-cost email tool to enable sending password reset links to users. | Narendra |
| Rejection reason field | Add a non-mandatory text field for entering the reason when rejecting a visitor, and verify whether this feature already exists. | Narendra |
| Dashboard visualization | Enhance the dashboard with charts for top visitors, recent activity, and month-wise statistics. | Narendra |
| Quick-approval actions | Add quick-approve buttons to the dashboard for pending visitor approvals. | Narendra |

## 11. Glossary

| Term | Definition |
| --- | --- |
| Soft Delete | A deletion method where a record is flagged as deleted in the database rather than being physically removed, preserving history and auditability. |
| Pass Type | A category of visitor pass (e.g., duration or access level) selected during visitor entry. |
| Approver | The Admin or Super Admin designated to review and approve/reject a specific visitor entry. |
| Location Autofill | A feature that pre-populates the office location field based on the device's detected location. |
| Device Certificate | Credential information captured for a visitor's device to support IT/security provisioning. |



### Create a new good looking professional website and it should be responsive and looks best and make a functinoal backend that can interact with the DB in the backend and frontend 

### Make sure everything were built seamlessly all data structures must be same from DB, Frontend and backend