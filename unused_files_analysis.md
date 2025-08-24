# Unused Files Analysis Report

This document provides a comprehensive analysis of unused files in the IQAC-Suite repository.

## Executive Summary

- **Total Files Analyzed**: 168 files (80 static + 88 templates)
- **Unused Files Found**: 19 files (11.3% of total)
  - 13 unused static files (16.3% of static files)
  - 6 unused template files (6.8% of template files)
- **Python Files**: All 91 Python files are in use (0% unused)

## Methodology

The analysis was performed using multiple approaches:
1. **Static Analysis**: Scanned all HTML templates for static file references (`{% static %}` tags, CSS/JS includes)
2. **Template Analysis**: Scanned Python files for template references (`render()`, `TemplateResponse`, etc.)
3. **Cross-Reference**: Checked Django template inheritance and includes
4. **Manual Verification**: Performed targeted searches to confirm findings

## Detailed Findings

### Unused Static Files (13 files)

#### CSS Files
- `emt/static/emt/css/submit_event_report.css`
- `emt/static/emt/css/event_report_details.css`
- `emt/static/emt/css/typeahead-modern.css`

#### JavaScript Files
- `emt/static/emt/js/typeahead-init.js`
- `emt/static/emt/js/report_navigation.js`
- `emt/static/emt/js/org_picker.js`
- `static/core/js/admin_dashboard.js`
- `static/core/js/Registration_form.js`
- `static/core/js/admin_settings.js`
- `static/core/js/header.js`

#### Images and Assets
- `emt/static/emt/img/ai-logo.svg`
- `transcript/static/student_pics/sakura.jpg`

#### Test Files
- `visual-tests/critical.spec.js`

### Unused Template Files (6 files)

#### Core Admin Templates
- `core/templates/core_admin_org_users/class_detail_redesigned.html`
- `core/templates/core_admin_org_users/select_role.html`
- `templates/core/admin_view_roles.html`

#### EMT Module Templates
- `emt/templates/emt/iqac_suite_dashboard.html`
- `emt/templates/emt/cdl_dashboard.html`

#### Partial Templates
- `templates/partials/master_data_widget.html`

**Note**: `templates/core/admin_sidebar_permissions.html` was initially flagged but is actually in use (referenced in core/urls.py and core/views.py).

## File Categories by Type

### Static Files Breakdown
| File Type | Total | Used | Unused | Usage Rate |
|-----------|-------|------|--------|------------|
| CSS       | 21    | 18   | 3      | 85.7%      |
| JavaScript| 21    | 14   | 7      | 66.7%      |
| Images    | 30    | 28   | 2      | 93.3%      |
| Other     | 8     | 7    | 1      | 87.5%      |

### Application Module Analysis
| Module     | Unused Static | Unused Templates | Notes |
|------------|---------------|------------------|-------|
| EMT        | 6 files       | 2 files         | Event Management module |
| Core       | 4 files       | 4 files         | Core application |
| Transcript | 1 file        | 0 files         | Transcript module |
| Visual Tests| 1 file       | 0 files         | Testing infrastructure |
| Partials   | 0 files       | 1 file          | Shared template components |

## Recommendations

### Immediate Actions
1. **Review and Remove**: Consider removing confirmed unused files after final verification
2. **Archive**: Move potentially useful but currently unused files to an archive directory
3. **Documentation**: Update any documentation that references removed files

### Files Requiring Careful Review
The following files should be reviewed more carefully before removal:

1. **`visual-tests/critical.spec.js`**: This appears to be a test file and might be used by CI/CD
2. **Template files with "redesigned" in name**: May be newer versions meant to replace existing templates
3. **Admin dashboard and settings JS files**: May be loaded conditionally or in specific admin contexts

### Best Practices Going Forward
1. **Regular Cleanup**: Perform this analysis quarterly to prevent accumulation of unused files
2. **Code Reviews**: Include file usage verification in code review processes
3. **Documentation**: Maintain clear documentation about file purposes and dependencies

## Notes and Limitations

1. **Dynamic References**: This analysis may not catch dynamically constructed file paths
2. **Conditional Loading**: Some files might be loaded conditionally based on user roles or features
3. **External References**: Files referenced from external systems or configurations may not be detected
4. **Future Features**: Some files might be prepared for upcoming features

## Next Steps

1. Manually verify each identified file before removal
2. Check with development team about the purpose of files with unclear usage
3. Create backup/archive of files before deletion
4. Update build processes and documentation as needed

---

**Analysis Date**: Sun Aug 24 14:48:36 UTC 2025
**Repository**: IQAC-Suite
**Commit**: f86776b99df90a5604c702d1d824a014125e2243

