# Database Schema

## Core

### OrganizationType (core_organizationtype)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |
| is_active | BooleanField | False | False |  |
| can_have_parent | BooleanField | False | False |  |
| parent_type | ForeignKey | True | False | core.OrganizationType |

### Organization (core_organization)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |
| org_type | ForeignKey | False | False | core.OrganizationType |
| is_active | BooleanField | False | False |  |
| parent | ForeignKey | True | False | core.Organization |
| code | CharField | True | False |  |
| meta | JSONField | False | False |  |

### OrganizationRole (core_organizationrole)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| status | CharField | False | False |  |
| archived_at | DateTimeField | True | False |  |
| archived_by | ForeignKey | True | False | auth.User |
| organization | ForeignKey | False | False | core.Organization |
| name | CharField | False | False |  |
| is_active | BooleanField | False | False |  |
| description | TextField | True | False |  |

### RoleAssignment (core_roleassignment)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | False | False | auth.User |
| role | ForeignKey | True | False | core.OrganizationRole |
| organization | ForeignKey | True | False | core.Organization |
| academic_year | CharField | True | False |  |
| class_name | CharField | True | False |  |

### OrganizationMembership (core_organizationmembership)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | False | False | auth.User |
| organization | ForeignKey | False | False | core.Organization |
| academic_year | CharField | False | False |  |
| role | CharField | False | False |  |
| is_primary | BooleanField | False | False |  |
| is_active | BooleanField | False | False |  |
| created_at | DateTimeField | False | False |  |

### Profile (core_profile)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | OneToOneField | False | False | auth.User |
| register_no | CharField | True | False |  |
| role | CharField | False | False |  |
| activated_at | DateTimeField | True | False |  |

### Report (core_report)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| title | CharField | False | False |  |
| description | TextField | False | False |  |
| organization | ForeignKey | True | False | core.Organization |
| submitted_by | ForeignKey | True | False | auth.User |
| created_at | DateTimeField | False | False |  |
| report_type | CharField | False | False |  |
| file | FileField | True | False |  |
| status | CharField | False | False |  |
| feedback | TextField | True | False |  |

### Program (core_program)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| status | CharField | False | False |  |
| archived_at | DateTimeField | True | False |  |
| archived_by | ForeignKey | True | False | auth.User |
| name | CharField | False | False |  |
| organization | ForeignKey | True | False | core.Organization |

### ProgramOutcome (core_programoutcome)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| status | CharField | False | False |  |
| archived_at | DateTimeField | True | False |  |
| archived_by | ForeignKey | True | False | auth.User |
| program | ForeignKey | False | False | core.Program |
| description | TextField | False | False |  |

### ProgramSpecificOutcome (core_programspecificoutcome)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| status | CharField | False | False |  |
| archived_at | DateTimeField | True | False |  |
| archived_by | ForeignKey | True | False | auth.User |
| program | ForeignKey | False | False | core.Program |
| description | TextField | False | False |  |

### POPSOAssignment (core_popsoassignment)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| organization | ForeignKey | False | False | core.Organization |
| assigned_user | ForeignKey | False | False | auth.User |
| assigned_by | ForeignKey | False | False | auth.User |
| assigned_at | DateTimeField | False | False |  |
| is_active | BooleanField | False | False |  |

### POPSOChangeNotification (core_popsochangenotification)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | False | False | auth.User |
| organization | ForeignKey | False | False | core.Organization |
| action | CharField | False | False |  |
| outcome_type | CharField | False | False |  |
| outcome_description | TextField | False | False |  |
| created_at | DateTimeField | False | False |  |
| is_read | BooleanField | False | False |  |

### SDGGoal (core_sdggoal)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |

### ApprovalFlowTemplate (core_approvalflowtemplate)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| status | CharField | False | False |  |
| archived_at | DateTimeField | True | False |  |
| archived_by | ForeignKey | True | False | auth.User |
| organization | ForeignKey | False | False | core.Organization |
| step_order | PositiveIntegerField | False | False |  |
| role_required | CharField | False | False |  |
| user | ForeignKey | True | False | auth.User |
| optional | BooleanField | False | False |  |

### ApprovalFlowConfig (core_approvalflowconfig)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| organization | OneToOneField | False | False | core.Organization |
| require_faculty_incharge_first | BooleanField | False | False |  |

### RoleEventApprovalVisibility (core_roleeventapprovalvisibility)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| role | OneToOneField | False | False | core.OrganizationRole |
| can_view | BooleanField | False | False |  |

### UserEventApprovalVisibility (core_usereventapprovalvisibility)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | False | False | auth.User |
| role | ForeignKey | False | False | core.OrganizationRole |
| can_view | BooleanField | False | False |  |

### Class (core_class)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |
| code | CharField | False | False |  |
| organization | ForeignKey | True | False | core.Organization |
| academic_year | CharField | True | False |  |
| teacher | ForeignKey | True | False | auth.User |
| is_active | BooleanField | False | False |  |
| students | ManyToManyField | False | False | emt.Student |

### FacultyMeeting (core_facultymeeting)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| title | CharField | False | False |  |
| description | TextField | False | False |  |
| organization | ForeignKey | False | False | core.Organization |
| scheduled_at | DateTimeField | False | False |  |
| created_by | ForeignKey | False | False | auth.User |
| created_at | DateTimeField | False | False |  |

### ImpersonationLog (core_impersonationlog)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| original_user | ForeignKey | False | False | auth.User |
| impersonated_user | ForeignKey | False | False | auth.User |
| started_at | DateTimeField | False | False |  |
| ended_at | DateTimeField | True | False |  |
| ip_address | GenericIPAddressField | True | False |  |
| user_agent | TextField | True | False |  |

### ActivityLog (core_activitylog)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | True | False | auth.User |
| action | CharField | False | False |  |
| description | TextField | False | False |  |
| timestamp | DateTimeField | False | False |  |
| ip_address | GenericIPAddressField | True | False |  |
| metadata | JSONField | True | False |  |

### CDLRequest (core_cdlrequest)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| wants_cdl | BooleanField | False | False |  |
| need_poster | BooleanField | False | False |  |
| poster_mode | CharField | False | False |  |
| poster_organization_name | CharField | False | False |  |
| poster_time | CharField | False | False |  |
| poster_date | CharField | False | False |  |
| poster_venue | CharField | False | False |  |
| poster_resource_person | CharField | False | False |  |
| poster_resource_designation | CharField | False | False |  |
| poster_title | CharField | False | False |  |
| poster_summary | TextField | False | False |  |
| poster_design_link | CharField | False | False |  |
| poster_final_approved | BooleanField | False | False |  |
| svc_photography | BooleanField | False | False |  |
| svc_videography | BooleanField | False | False |  |
| svc_digital_board | BooleanField | False | False |  |
| svc_voluntary_cards | BooleanField | False | False |  |
| need_certificate_any | BooleanField | False | False |  |
| need_certificate_cdl | BooleanField | False | False |  |
| certificate_mode | CharField | False | False |  |
| certificate_design_link | CharField | False | False |  |
| combined_design_link | CharField | False | False |  |
| created_at | DateTimeField | False | False |  |
| updated_at | DateTimeField | False | False |  |

### CDLCommunicationThread (core_cdlcommunicationthread)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| created_at | DateTimeField | False | False |  |

### CDLMessage (core_cdlmessage)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| thread | ForeignKey | False | False | core.CDLCommunicationThread |
| author | ForeignKey | False | False | auth.User |
| body | TextField | False | False |  |
| file | FileField | True | False |  |
| sent_via_email | BooleanField | False | False |  |
| created_at | DateTimeField | False | False |  |

### CertificateBatch (core_certificatebatch)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | ForeignKey | False | False | emt.EventProposal |
| csv_file | FileField | False | False |  |
| ai_check_status | CharField | False | False |  |
| notes | TextField | False | False |  |
| created_at | DateTimeField | False | False |  |
| updated_at | DateTimeField | False | False |  |

### CertificateEntry (core_certificateentry)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| batch | ForeignKey | False | False | core.CertificateBatch |
| name | CharField | False | False |  |
| role | CharField | False | False |  |
| custom_role_text | CharField | False | False |  |
| ai_valid | BooleanField | False | False |  |
| ai_errors | TextField | False | False |  |
| ready_for_cdl | BooleanField | False | False |  |

### SidebarPermission (core_sidebarpermission)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | True | False | auth.User |
| role | CharField | False | False |  |
| items | JSONField | False | False |  |

### DashboardAssignment (core_dashboardassignment)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | True | False | auth.User |
| role | CharField | False | False |  |
| organization_type | ForeignKey | True | False | core.OrganizationType |
| dashboard | CharField | False | False |  |
| is_active | BooleanField | False | False |  |
| created_at | DateTimeField | False | False |  |

## Emt

### EventProposal (emt_eventproposal)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| submitted_by | ForeignKey | False | False | auth.User |
| organization | ForeignKey | True | False | core.Organization |
| needs_finance_approval | BooleanField | False | False |  |
| is_big_event | BooleanField | False | False |  |
| committees | TextField | False | False |  |
| committees_collaborations | TextField | False | False |  |
| event_title | CharField | False | False |  |
| num_activities | PositiveIntegerField | True | False |  |
| event_datetime | DateTimeField | True | False |  |
| event_start_date | DateField | True | False |  |
| event_end_date | DateField | True | False |  |
| venue | CharField | False | False |  |
| academic_year | CharField | False | False |  |
| target_audience | CharField | False | False |  |
| pos_pso | TextField | False | False |  |
| student_coordinators | TextField | False | False |  |
| event_focus_type | CharField | False | False |  |
| report_generated | BooleanField | False | False |  |
| report_assigned_to | ForeignKey | True | False | auth.User |
| report_assigned_at | DateTimeField | True | False |  |
| fest_fee_participants | PositiveIntegerField | True | False |  |
| fest_fee_rate | DecimalField | True | False |  |
| fest_fee_amount | DecimalField | True | False |  |
| fest_sponsorship_amount | DecimalField | True | False |  |
| conf_fee_participants | PositiveIntegerField | True | False |  |
| conf_fee_rate | DecimalField | True | False |  |
| conf_fee_amount | DecimalField | True | False |  |
| conf_sponsorship_amount | DecimalField | True | False |  |
| created_at | DateTimeField | False | False |  |
| updated_at | DateTimeField | False | False |  |
| status | CharField | False | False |  |
| sdg_goals | ManyToManyField | False | False | core.SDGGoal |
| faculty_incharges | ManyToManyField | False | False | auth.User |

### EventNeedAnalysis (emt_eventneedanalysis)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| content | TextField | False | False |  |

### EventObjectives (emt_eventobjectives)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| content | TextField | False | False |  |

### EventExpectedOutcomes (emt_eventexpectedoutcomes)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| content | TextField | False | False |  |

### TentativeFlow (emt_tentativeflow)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| content | TextField | False | False |  |

### EventActivity (emt_eventactivity)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | ForeignKey | False | False | emt.EventProposal |
| name | CharField | False | False |  |
| date | DateField | False | False |  |

### SpeakerProfile (emt_speakerprofile)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | ForeignKey | False | False | emt.EventProposal |
| full_name | CharField | False | False |  |
| designation | CharField | False | False |  |
| affiliation | CharField | False | False |  |
| contact_email | CharField | False | False |  |
| contact_number | CharField | False | False |  |
| linkedin_url | CharField | True | False |  |
| photo | FileField | True | False |  |
| detailed_profile | TextField | False | False |  |

### ExpenseDetail (emt_expensedetail)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | ForeignKey | False | False | emt.EventProposal |
| sl_no | PositiveIntegerField | False | False |  |
| particulars | CharField | False | False |  |
| amount | DecimalField | False | False |  |

### IncomeDetail (emt_incomedetail)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | ForeignKey | False | False | emt.EventProposal |
| sl_no | PositiveIntegerField | False | False |  |
| particulars | CharField | False | False |  |
| participants | PositiveIntegerField | False | False |  |
| rate | DecimalField | False | False |  |
| amount | DecimalField | False | False |  |

### ApprovalStep (emt_approvalstep)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | ForeignKey | False | False | emt.EventProposal |
| step_order | PositiveIntegerField | True | False |  |
| order_index | PositiveIntegerField | False | False |  |
| role_required | CharField | True | False |  |
| assigned_to | ForeignKey | True | False | auth.User |
| approved_by | ForeignKey | True | False | auth.User |
| approved_at | DateTimeField | True | False |  |
| is_optional | BooleanField | False | False |  |
| optional_unlocked | BooleanField | False | False |  |
| status | CharField | False | False |  |
| decided_by | ForeignKey | True | False | auth.User |
| decided_at | DateTimeField | True | False |  |
| note | TextField | False | False |  |
| comment | TextField | False | False |  |

### MediaRequest (emt_mediarequest)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | ForeignKey | False | False | auth.User |
| media_type | CharField | False | False |  |
| title | CharField | False | False |  |
| description | TextField | False | False |  |
| event_date | DateField | False | False |  |
| media_file | FileField | True | False |  |
| status | CharField | False | False |  |
| created_at | DateTimeField | False | False |  |

### CDLSupport (emt_cdlsupport)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| needs_support | BooleanField | False | False |  |
| poster_required | BooleanField | False | False |  |
| poster_choice | CharField | False | False |  |
| organization_name | CharField | False | False |  |
| poster_time | CharField | False | False |  |
| poster_date | DateField | True | False |  |
| poster_venue | CharField | False | False |  |
| resource_person_name | CharField | False | False |  |
| resource_person_designation | CharField | False | False |  |
| poster_event_title | CharField | False | False |  |
| poster_summary | TextField | False | False |  |
| poster_design_link | CharField | False | False |  |
| other_services | JSONField | False | False |  |
| certificates_required | BooleanField | False | False |  |
| certificate_help | BooleanField | False | False |  |
| certificate_choice | CharField | False | False |  |
| certificate_design_link | CharField | False | False |  |
| blog_content | TextField | False | False |  |

### CDLCertificateRecipient (emt_cdlcertificaterecipient)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| support | ForeignKey | False | False | emt.CDLSupport |
| name | CharField | False | False |  |
| role | CharField | False | False |  |
| certificate_type | CharField | False | False |  |
| ai_approved | BooleanField | False | False |  |
| created_at | DateTimeField | False | False |  |

### CDLMessage (emt_cdlmessage)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| support | ForeignKey | False | False | emt.CDLSupport |
| sender | ForeignKey | False | False | auth.User |
| message | TextField | False | False |  |
| file | FileField | True | False |  |
| via_email | BooleanField | False | False |  |
| created_at | DateTimeField | False | False |  |

### EventReport (emt_eventreport)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| proposal | OneToOneField | False | False | emt.EventProposal |
| location | CharField | False | False |  |
| blog_link | CharField | False | False |  |
| actual_event_type | CharField | False | False |  |
| num_student_volunteers | PositiveIntegerField | True | False |  |
| num_participants | PositiveIntegerField | True | False |  |
| num_student_participants | PositiveIntegerField | True | False |  |
| num_faculty_participants | PositiveIntegerField | True | False |  |
| num_external_participants | PositiveIntegerField | True | False |  |
| organizing_committee | TextField | False | False |  |
| actual_speakers | TextField | False | False |  |
| external_contact_details | TextField | False | False |  |
| summary | TextField | False | False |  |
| key_achievements | TextField | False | False |  |
| notable_moments | TextField | False | False |  |
| outcomes | TextField | False | False |  |
| learning_outcomes | TextField | False | False |  |
| participant_feedback | TextField | False | False |  |
| measurable_outcomes | TextField | False | False |  |
| impact_assessment | TextField | False | False |  |
| analysis | TextField | False | False |  |
| objective_achievement | TextField | False | False |  |
| strengths_analysis | TextField | False | False |  |
| challenges_analysis | TextField | False | False |  |
| effectiveness_analysis | TextField | False | False |  |
| lessons_learned | TextField | False | False |  |
| impact_on_stakeholders | TextField | False | False |  |
| innovations_best_practices | TextField | False | False |  |
| pos_pso_mapping | TextField | False | False |  |
| needs_grad_attr_mapping | TextField | False | False |  |
| contemporary_requirements | TextField | False | False |  |
| sdg_value_systems_mapping | TextField | False | False |  |
| iqac_feedback | TextField | False | False |  |
| report_signed_date | DateField | False | False |  |
| beneficiaries_details | TextField | False | False |  |
| attendance_notes | TextField | False | False |  |
| ai_generated_report | TextField | True | False |  |
| created_at | DateTimeField | False | False |  |
| updated_at | DateTimeField | False | False |  |

### EventReportAttachment (emt_eventreportattachment)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| report | ForeignKey | False | False | emt.EventReport |
| file | FileField | False | False |  |
| caption | CharField | False | False |  |

### AttendanceRow (emt_attendancerow)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| event_report | ForeignKey | False | False | emt.EventReport |
| registration_no | CharField | False | False |  |
| full_name | CharField | False | False |  |
| student_class | CharField | False | False |  |
| absent | BooleanField | False | False |  |
| volunteer | BooleanField | False | False |  |

### Student (emt_student)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| user | OneToOneField | False | False | auth.User |
| mentor | ForeignKey | True | False | auth.User |
| registration_number | CharField | False | False |  |
| gpa | DecimalField | True | False |  |
| attendance | DecimalField | True | False |  |
| events | ManyToManyField | False | False | emt.EventProposal |

## Transcript

### GraduateAttribute (transcript_graduateattribute)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |

### CharacterStrength (transcript_characterstrength)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |

### AttributeStrengthMap (transcript_attributestrengthmap)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| graduate_attribute | ForeignKey | False | False | transcript.GraduateAttribute |
| character_strength | ForeignKey | False | False | transcript.CharacterStrength |
| weight | FloatField | False | False |  |

### AcademicYear (transcript_academicyear)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| year | CharField | False | False |  |
| start_date | DateField | True | False |  |
| end_date | DateField | True | False |  |
| is_active | BooleanField | False | False |  |

### School (transcript_school)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |

### Course (transcript_course)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |
| school | ForeignKey | False | False | transcript.School |

### Event (transcript_event)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |
| date | DateField | False | False |  |
| attributes | ManyToManyField | False | False | transcript.GraduateAttribute |

### Student (transcript_student)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| roll_no | CharField | False | False |  |
| name | CharField | False | False |  |
| photo | FileField | True | False |  |
| school | ForeignKey | True | False | transcript.School |
| course | ForeignKey | True | False | transcript.Course |
| academic_year | ForeignKey | True | False | transcript.AcademicYear |

### Role (transcript_role)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| name | CharField | False | False |  |
| factor | FloatField | False | False |  |

### Participation (transcript_participation)
| Field | Type | Null | Primary Key | Related Model |
|-------|------|------|-------------|---------------|
| id | BigAutoField | False | True |  |
| student | ForeignKey | False | False | transcript.Student |
| event | ForeignKey | False | False | transcript.Event |
| role | ForeignKey | False | False | transcript.Role |
