# .NET EditorConfig Standard

> Microsoft-aligned EditorConfig for C# projects with Roslyn analyzers.

---

## Installation

Copy `.editorconfig` to repo root. Applies automatically to all C# files.

### Required NuGet Package

```xml
<!-- Directory.Build.props -->
<Project>
  <PropertyGroup>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <AnalysisMode>Recommended</AnalysisMode>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
```

---

## EditorConfig Template

```ini
# .editorconfig
# Remove the line below if you want to inherit .editorconfig settings from higher directories
root = true

# =============================================================================
# ALL FILES
# =============================================================================
[*]
indent_style = space
indent_size = 4
end_of_line = crlf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

# =============================================================================
# C# FILES
# =============================================================================
[*.cs]

# -----------------------------------------------------------------------------
# LANGUAGE CONVENTIONS
# -----------------------------------------------------------------------------

# var preferences (Microsoft official: use var when type is obvious)
csharp_style_var_for_built_in_types = false:suggestion
csharp_style_var_when_type_is_apparent = true:suggestion
csharp_style_var_elsewhere = false:suggestion

# Expression-bodied members
csharp_style_expression_bodied_methods = when_on_single_line:suggestion
csharp_style_expression_bodied_constructors = false:suggestion
csharp_style_expression_bodied_operators = when_on_single_line:suggestion
csharp_style_expression_bodied_properties = true:suggestion
csharp_style_expression_bodied_indexers = true:suggestion
csharp_style_expression_bodied_accessors = true:suggestion
csharp_style_expression_bodied_lambdas = true:suggestion
csharp_style_expression_bodied_local_functions = when_on_single_line:suggestion

# Pattern matching
csharp_style_pattern_matching_over_is_with_cast_check = true:warning
csharp_style_pattern_matching_over_as_with_null_check = true:warning
csharp_style_prefer_switch_expression = true:suggestion
csharp_style_prefer_pattern_matching = true:suggestion
csharp_style_prefer_not_pattern = true:suggestion
csharp_style_prefer_extended_property_pattern = true:suggestion

# Null checking
csharp_style_throw_expression = true:suggestion
csharp_style_conditional_delegate_call = true:warning
csharp_style_prefer_null_check_over_type_check = true:suggestion
csharp_style_coalesce_expression = true:suggestion
csharp_style_null_propagation = true:suggestion

# Code block preferences
csharp_prefer_braces = true:warning
csharp_prefer_simple_using_statement = true:suggestion
csharp_style_namespace_declarations = file_scoped:warning
csharp_style_prefer_top_level_statements = true:suggestion

# Expression-level preferences
csharp_prefer_simple_default_expression = true:suggestion
csharp_style_prefer_local_over_anonymous_function = true:suggestion
csharp_style_prefer_index_operator = true:suggestion
csharp_style_prefer_range_operator = true:suggestion
csharp_style_implicit_object_creation_when_type_is_apparent = true:suggestion
csharp_style_prefer_tuple_swap = true:suggestion
csharp_style_prefer_utf8_string_literals = true:suggestion
csharp_style_inlined_variable_declaration = true:suggestion
csharp_style_deconstructed_variable_declaration = true:suggestion

# 'using' directive preferences
csharp_using_directive_placement = outside_namespace:warning

# Modifier preferences
csharp_prefer_static_local_function = true:suggestion
csharp_preferred_modifier_order = public,private,protected,internal,file,static,extern,new,virtual,abstract,sealed,override,readonly,unsafe,required,volatile,async:warning
csharp_style_prefer_readonly_struct = true:suggestion
csharp_style_prefer_readonly_struct_member = true:suggestion

# Primary constructor
csharp_style_prefer_primary_constructors = true:suggestion

# -----------------------------------------------------------------------------
# FORMATTING CONVENTIONS
# -----------------------------------------------------------------------------

# Newline options
csharp_new_line_before_open_brace = all
csharp_new_line_before_else = true
csharp_new_line_before_catch = true
csharp_new_line_before_finally = true
csharp_new_line_before_members_in_object_initializers = true
csharp_new_line_before_members_in_anonymous_types = true
csharp_new_line_between_query_expression_clauses = true

# Indentation options
csharp_indent_case_contents = true
csharp_indent_switch_labels = true
csharp_indent_labels = one_less_than_current
csharp_indent_block_contents = true
csharp_indent_braces = false
csharp_indent_case_contents_when_block = false

# Spacing options
csharp_space_after_cast = false
csharp_space_after_keywords_in_control_flow_statements = true
csharp_space_between_parentheses = false
csharp_space_before_colon_in_inheritance_clause = true
csharp_space_after_colon_in_inheritance_clause = true
csharp_space_around_binary_operators = before_and_after
csharp_space_between_method_declaration_parameter_list_parentheses = false
csharp_space_between_method_declaration_empty_parameter_list_parentheses = false
csharp_space_between_method_declaration_name_and_open_parenthesis = false
csharp_space_between_method_call_parameter_list_parentheses = false
csharp_space_between_method_call_empty_parameter_list_parentheses = false
csharp_space_between_method_call_name_and_opening_parenthesis = false
csharp_space_after_comma = true
csharp_space_before_comma = false
csharp_space_after_dot = false
csharp_space_before_dot = false
csharp_space_after_semicolon_in_for_statement = true
csharp_space_before_semicolon_in_for_statement = false
csharp_space_around_declaration_statements = false
csharp_space_before_open_square_brackets = false
csharp_space_between_empty_square_brackets = false
csharp_space_between_square_brackets = false

# Wrapping options
csharp_preserve_single_line_statements = false
csharp_preserve_single_line_blocks = true

# -----------------------------------------------------------------------------
# NAMING CONVENTIONS
# -----------------------------------------------------------------------------

# Symbols
dotnet_naming_symbols.public_members.applicable_kinds = property,method,event,delegate
dotnet_naming_symbols.public_members.applicable_accessibilities = public,internal,protected,protected_internal

dotnet_naming_symbols.private_fields.applicable_kinds = field
dotnet_naming_symbols.private_fields.applicable_accessibilities = private

dotnet_naming_symbols.private_static_fields.applicable_kinds = field
dotnet_naming_symbols.private_static_fields.applicable_accessibilities = private
dotnet_naming_symbols.private_static_fields.required_modifiers = static

dotnet_naming_symbols.constants.applicable_kinds = field
dotnet_naming_symbols.constants.required_modifiers = const

dotnet_naming_symbols.interfaces.applicable_kinds = interface

dotnet_naming_symbols.type_parameters.applicable_kinds = type_parameter

dotnet_naming_symbols.async_methods.applicable_kinds = method
dotnet_naming_symbols.async_methods.required_modifiers = async

# Styles
dotnet_naming_style.pascal_case.capitalization = pascal_case

dotnet_naming_style._camel_case.capitalization = camel_case
dotnet_naming_style._camel_case.required_prefix = _

dotnet_naming_style.s_camel_case.capitalization = camel_case
dotnet_naming_style.s_camel_case.required_prefix = s_

dotnet_naming_style.i_pascal_case.capitalization = pascal_case
dotnet_naming_style.i_pascal_case.required_prefix = I

dotnet_naming_style.t_pascal_case.capitalization = pascal_case
dotnet_naming_style.t_pascal_case.required_prefix = T

dotnet_naming_style.async_suffix.capitalization = pascal_case
dotnet_naming_style.async_suffix.required_suffix = Async

# Rules
dotnet_naming_rule.interfaces_must_be_pascal_case_with_i_prefix.symbols = interfaces
dotnet_naming_rule.interfaces_must_be_pascal_case_with_i_prefix.style = i_pascal_case
dotnet_naming_rule.interfaces_must_be_pascal_case_with_i_prefix.severity = warning

dotnet_naming_rule.type_parameters_must_be_pascal_case_with_t_prefix.symbols = type_parameters
dotnet_naming_rule.type_parameters_must_be_pascal_case_with_t_prefix.style = t_pascal_case
dotnet_naming_rule.type_parameters_must_be_pascal_case_with_t_prefix.severity = warning

dotnet_naming_rule.private_fields_must_be_camel_case_with_underscore.symbols = private_fields
dotnet_naming_rule.private_fields_must_be_camel_case_with_underscore.style = _camel_case
dotnet_naming_rule.private_fields_must_be_camel_case_with_underscore.severity = warning

dotnet_naming_rule.private_static_fields_must_be_camel_case_with_s_prefix.symbols = private_static_fields
dotnet_naming_rule.private_static_fields_must_be_camel_case_with_s_prefix.style = s_camel_case
dotnet_naming_rule.private_static_fields_must_be_camel_case_with_s_prefix.severity = warning

dotnet_naming_rule.constants_must_be_pascal_case.symbols = constants
dotnet_naming_rule.constants_must_be_pascal_case.style = pascal_case
dotnet_naming_rule.constants_must_be_pascal_case.severity = warning

dotnet_naming_rule.async_methods_must_have_async_suffix.symbols = async_methods
dotnet_naming_rule.async_methods_must_have_async_suffix.style = async_suffix
dotnet_naming_rule.async_methods_must_have_async_suffix.severity = suggestion

dotnet_naming_rule.public_members_must_be_pascal_case.symbols = public_members
dotnet_naming_rule.public_members_must_be_pascal_case.style = pascal_case
dotnet_naming_rule.public_members_must_be_pascal_case.severity = warning

# -----------------------------------------------------------------------------
# .NET CODE STYLE
# -----------------------------------------------------------------------------

# this. and Me. preferences
dotnet_style_qualification_for_field = false:suggestion
dotnet_style_qualification_for_property = false:suggestion
dotnet_style_qualification_for_method = false:suggestion
dotnet_style_qualification_for_event = false:suggestion

# Language keywords vs BCL types
dotnet_style_predefined_type_for_locals_parameters_members = true:warning
dotnet_style_predefined_type_for_member_access = true:warning

# Modifier preferences
dotnet_style_require_accessibility_modifiers = for_non_interface_members:warning
dotnet_style_readonly_field = true:warning

# Parentheses preferences
dotnet_style_parentheses_in_arithmetic_binary_operators = always_for_clarity:suggestion
dotnet_style_parentheses_in_relational_binary_operators = always_for_clarity:suggestion
dotnet_style_parentheses_in_other_binary_operators = always_for_clarity:suggestion
dotnet_style_parentheses_in_other_operators = never_if_unnecessary:suggestion

# Expression-level preferences
dotnet_style_object_initializer = true:suggestion
dotnet_style_collection_initializer = true:suggestion
dotnet_style_explicit_tuple_names = true:warning
dotnet_style_prefer_inferred_tuple_names = true:suggestion
dotnet_style_prefer_inferred_anonymous_type_member_names = true:suggestion
dotnet_style_prefer_auto_properties = true:suggestion
dotnet_style_prefer_conditional_expression_over_assignment = true:suggestion
dotnet_style_prefer_conditional_expression_over_return = true:suggestion
dotnet_style_prefer_compound_assignment = true:suggestion
dotnet_style_prefer_simplified_interpolation = true:suggestion
dotnet_style_prefer_simplified_boolean_expressions = true:suggestion
dotnet_style_prefer_collection_expression = when_types_loosely_match:suggestion

# Null-checking preferences
dotnet_style_coalesce_expression = true:suggestion
dotnet_style_null_propagation = true:suggestion
dotnet_style_prefer_is_null_check_over_reference_equality_method = true:warning

# File header
file_header_template = unset

# Unnecessary code
dotnet_code_quality_unused_parameters = all:warning
dotnet_remove_unnecessary_suppression_exclusions = none

# -----------------------------------------------------------------------------
# ANALYZER SEVERITY
# -----------------------------------------------------------------------------

# Code Quality
dotnet_diagnostic.CA1062.severity = warning    # Validate arguments of public methods
dotnet_diagnostic.CA1303.severity = none       # Do not pass literals as localized parameters
dotnet_diagnostic.CA1304.severity = warning    # Specify CultureInfo
dotnet_diagnostic.CA1305.severity = warning    # Specify IFormatProvider
dotnet_diagnostic.CA1307.severity = warning    # Specify StringComparison
dotnet_diagnostic.CA1310.severity = warning    # Specify StringComparison for correctness
dotnet_diagnostic.CA1507.severity = warning    # Use nameof
dotnet_diagnostic.CA1707.severity = warning    # Remove underscores from member names
dotnet_diagnostic.CA1708.severity = warning    # Identifiers should differ by more than case
dotnet_diagnostic.CA1710.severity = warning    # Identifiers should have correct suffix
dotnet_diagnostic.CA1711.severity = warning    # Identifiers should not have incorrect suffix
dotnet_diagnostic.CA1716.severity = warning    # Identifiers should not match keywords
dotnet_diagnostic.CA1720.severity = warning    # Identifiers should not contain type names
dotnet_diagnostic.CA1724.severity = warning    # Type names should not match namespaces
dotnet_diagnostic.CA1805.severity = warning    # Do not initialize unnecessarily
dotnet_diagnostic.CA1806.severity = warning    # Do not ignore method results
dotnet_diagnostic.CA1812.severity = warning    # Avoid uninstantiated internal classes
dotnet_diagnostic.CA1816.severity = warning    # Call GC.SuppressFinalize correctly
dotnet_diagnostic.CA1822.severity = warning    # Mark members as static
dotnet_diagnostic.CA1825.severity = warning    # Avoid zero-length array allocations
dotnet_diagnostic.CA1827.severity = warning    # Do not use Count/LongCount when Any can be used
dotnet_diagnostic.CA1829.severity = warning    # Use Length/Count property
dotnet_diagnostic.CA1834.severity = warning    # Use StringBuilder.Append(char)
dotnet_diagnostic.CA1847.severity = warning    # Use string.Contains(char)
dotnet_diagnostic.CA1848.severity = suggestion # Use LoggerMessage delegates
dotnet_diagnostic.CA1860.severity = warning    # Avoid using Enumerable.Any() extension method
dotnet_diagnostic.CA2000.severity = warning    # Dispose objects before losing scope
dotnet_diagnostic.CA2007.severity = none       # Do not directly await a Task (library only)
dotnet_diagnostic.CA2008.severity = warning    # Do not create tasks without passing a TaskScheduler
dotnet_diagnostic.CA2012.severity = warning    # Use ValueTasks correctly
dotnet_diagnostic.CA2016.severity = warning    # Forward CancellationToken
dotnet_diagnostic.CA2100.severity = warning    # Review SQL queries for security
dotnet_diagnostic.CA2213.severity = warning    # Disposable fields should be disposed
dotnet_diagnostic.CA2234.severity = warning    # Pass System.Uri objects instead of strings
dotnet_diagnostic.CA2241.severity = warning    # Provide correct arguments to formatting methods
dotnet_diagnostic.CA2254.severity = warning    # Template should be a static expression

# IDE rules
dotnet_diagnostic.IDE0005.severity = warning   # Remove unnecessary using directives
dotnet_diagnostic.IDE0058.severity = none      # Expression value is never used
dotnet_diagnostic.IDE0060.severity = warning   # Remove unused parameter
dotnet_diagnostic.IDE0063.severity = suggestion # Use simple 'using' statement
dotnet_diagnostic.IDE0065.severity = warning   # 'using' directive placement
dotnet_diagnostic.IDE0090.severity = suggestion # Simplify new expression
dotnet_diagnostic.IDE0130.severity = warning   # Namespace does not match folder structure
dotnet_diagnostic.IDE0161.severity = warning   # Use file-scoped namespace

# =============================================================================
# OTHER FILE TYPES
# =============================================================================

[*.{xml,csproj,props,targets}]
indent_size = 2

[*.{json,yml,yaml}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[*.{sh,bash}]
end_of_line = lf
```

---

## Verification Commands

```bash
# Check formatting (CI/CD)
dotnet format --verify-no-changes --verbosity diagnostic

# Fix formatting locally
dotnet format
```
