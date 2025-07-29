# Implementation Plan: BVSim - Beach Volleyball Point Simulator

**Feature Branch**: `001-bvsim-volleyball-simulator`  
**Created**: 2025-07-24  
**Specification**: [Feature Specification](./feature-spec.md)  

---

## ⚡ Quick Guidelines

**Note**: This document serves two purposes:
1. **As a template** - For AIs/humans creating implementation plans
2. **As a guide** - For AIs/humans executing the implementation

Instructions marked *(for execution)* apply when implementing the feature.
Instructions marked *(when creating this plan)* apply when filling out this template.

- ✅ Mark all technical decisions that need clarification
- ✅ Use [NEEDS CLARIFICATION: question] for any assumptions
- ❌ Don't guess at technical choices without context
- ❌ Don't include actual code - use pseudocode or references
- 📋 The review checklist acts as "unit tests" for this plan
- 📁 Extract details to `implementation-details/` files

---

## Executive Summary *(mandatory)*

BVSim will be implemented as a Python-based CLI application with three core libraries: a state machine library for volleyball point simulation, a probability engine for conditional probability calculations, and a statistics analyzer for simulation results and sensitivity analysis. The implementation follows a simple architecture using Python's built-in libraries for maximum portability and minimal dependencies.

## Requirements *(mandatory)*

**Minimum Versions**: Python 3.8+ (for dataclasses and typing support)  
**Dependencies**: PyYAML for configuration files, Python standard library (random, dataclasses, argparse, csv)  
**Technology Stack**: Pure Python CLI application with YAML configuration files, no external database or frameworks  
**Feature Spec Alignment**: [x] All requirements addressed

---

## Constitutional Compliance *(mandatory)*

### Simplicity Declaration (Articles VII & VIII)
- **Project Count**: 3 (bvsim-core, bvsim-stats, bvsim-cli)
- **Model Strategy**: [x] Single model - Direct dataclass models, no separate DTOs
- **Framework Usage**: [x] Direct - Using Python standard library directly
- **Patterns Used**: [x] None - Simple functions and classes only

### Testing Strategy (Articles III & IX)
- **Test Order**: Contract → Integration → E2E → Unit
- **Contract Location**: `/contracts/` (CLI command contracts)
- **Real Environments**: [x] Yes - No mocks, real file I/O and computation
- **Coverage Target**: 80% minimum, 100% critical paths (state machine, probability validation)

### Library Organization (Articles I & II)
- **Libraries**: 
  - bvsim-core: State machine and point simulation engine
  - bvsim-stats: Statistics aggregation and sensitivity analysis
  - bvsim-cli: Command-line interface and team configuration
- **CLI Interfaces**: 
  - bvsim-core: `simulate-point`, `validate-team`
  - bvsim-stats: `analyze-results`, `sensitivity-analysis`
  - bvsim-cli: `create-team`, `run-simulation`, `compare-teams`
- **CLI Standards**: All CLIs implement --help, --version, --format (json/text)
- **Inter-Library Contracts**: Defined in implementation-details/08-inter-library-tests.md

### Observability (Article V)
- [x] Structured logging planned (JSON format for simulation logs)
- [x] Error reporting defined (validation errors with specific contexts)
- [x] Metrics collection (point progression timing, validation statistics)

---

## Project Structure *(mandatory)*

```
001-bvsim-volleyball-simulator/
├── implementation-plan.md          # This document (HIGH-LEVEL ONLY)
├── manual-testing.md              # Step-by-step validation instructions
├── implementation-details/         # Detailed specifications
│   ├── 00-research.md             # Beach volleyball rules research
│   ├── 02-data-model.md           # Team, Point, State, Simulation schemas
│   ├── 03-api-contracts.md        # CLI command specifications
│   ├── 04-algorithms.md           # State machine logic and probability calculations
│   ├── 06-contract-tests.md       # CLI contract test specifications
│   ├── 07-integration-tests.md    # End-to-end simulation test scenarios
│   └── 08-inter-library-tests.md  # Library boundary tests
├── contracts/                      # CLI contracts (FIRST)
│   ├── bvsim-core-cli.md
│   ├── bvsim-stats-cli.md
│   └── bvsim-cli.md
├── src/
│   ├── bvsim_core/
│   │   ├── __init__.py
│   │   ├── state_machine.py       # Point progression state machine
│   │   ├── probability.py         # Conditional probability engine
│   │   ├── simulation.py          # Point simulation runner
│   │   └── cli.py                 # Core CLI interface
│   ├── bvsim_stats/
│   │   ├── __init__.py
│   │   ├── aggregator.py          # Statistics collection
│   │   ├── sensitivity.py         # Sensitivity analysis engine
│   │   └── cli.py                 # Stats CLI interface
│   └── bvsim_cli/
│       ├── __init__.py
│       ├── team_config.py         # Team definition and validation
│       ├── runner.py              # Main simulation orchestrator
│       └── cli.py                 # Main CLI interface
└── tests/
    ├── contract/                   # Contract tests (FIRST)
    ├── integration/                # Integration tests
    ├── inter-library/              # Cross-library tests
    └── unit/                       # Unit tests (LAST)
```

### File Creation Order
1. Create directory structure
2. Create `implementation-details/00-research.md` (beach volleyball rules validation)
3. Create `contracts/` with CLI command specifications
4. Create `implementation-details/02-data-model.md`, `03-api-contracts.md`, `04-algorithms.md`
5. Create test files in order: contract → integration → e2e → unit
6. Create source files to make tests pass
7. Create `manual-testing.md` for E2E validation

---

## Implementation Phases *(mandatory)*

### Phase -1: Pre-Implementation Gates

#### Technical Unknowns
- [x] Complex areas identified: Beach volleyball state machine transitions, conditional probability matrix validation
- [x] Research completed: Beach volleyball rules documented in implementation-details/00-research.md
*Research findings: implementation-details/00-research.md*

#### Simplicity Gate (Article VII)
- [x] Using ≤3 projects? Yes - core, stats, cli
- [x] No future-proofing? Yes - focused on point simulation only
- [x] No unnecessary patterns? Yes - simple functions and dataclasses

#### Anti-Abstraction Gate (Article VIII)
- [x] Using framework directly? Yes - Python standard library only
- [x] Single model representation? Yes - dataclasses for all entities
- [x] Concrete classes by default? Yes - no interfaces or abstract classes

#### Integration-First Gate (Article IX)
- [x] Contracts defined? Yes - CLI command contracts specified
- [x] Contract tests written? To be created in Phase 0
- [x] Integration plan ready? Yes - documented in implementation-details/

### Verification: Phase -1 Complete *(execution checkpoint)*
- [x] All gates passed or exceptions documented in Complexity Tracking
- [x] Research findings documented in implementation-details/00-research.md
- [x] Ready to create directory structure

### Phase 0: Contract & Test Setup

**Prerequisites** *(for execution)*: Phase -1 verification complete
**Deliverables** *(from execution)*: Failing contract tests, CLI specifications, test strategy

1. **Define CLI Contracts**
   ```pseudocode
   Create contracts/ directory with CLI command specifications
   Define all commands, arguments, input/output formats
   Document team configuration YAML schema
   Specify simulation output formats (YAML for configs, JSON for results)
   ```
   *Details: implementation-details/03-api-contracts.md*

2. **Write Contract Tests**
   ```pseudocode
   Create failing tests that verify CLI behavior matches contracts
   Test all commands with various input combinations
   Validate YAML team input schemas and JSON result output schemas
   Test error handling for invalid inputs
   ```
   *Detailed test scenarios: implementation-details/06-contract-tests.md*

3. **Design Integration Tests**
   ```pseudocode
   Plan end-to-end user workflow tests
   Plan library boundary tests between core/stats/cli
   Plan file I/O integration tests
   Plan large simulation performance tests
   ```
   *Test strategy details: implementation-details/07-integration-tests.md*
   *Inter-library tests: implementation-details/08-inter-library-tests.md*

4. **Create Manual Testing Guide**
   - Map each user story to validation steps
   - Document CLI usage examples for each feature
   - Create step-by-step validation procedures
   *Output: manual-testing.md*

### Verification: Phase 0 Complete *(execution checkpoint)*
- [ ] CLI contracts exist in `/contracts/`
- [ ] Contract tests written and failing
- [ ] Integration test plan documented
- [ ] Manual testing guide created
- [ ] All detail files referenced exist

### Phase 1: Core Implementation

**Prerequisites** *(for execution)*: Phase 0 verification complete
**Deliverables** *(from execution)*: Working implementation passing all contract tests

1. **Data Model Implementation**
   - Define Team, Point, State, Simulation dataclasses
   - Implement conditional probability matrix validation
   - Add YAML serialization/deserialization for team configs, JSON for results
   *Detailed schema and relationships: implementation-details/02-data-model.md*

2. **State Machine Implementation**
   - Implement beach volleyball point progression state machine
   - Add team role validation and state transition rules
   - Implement conditional probability lookups
   *Algorithm details: implementation-details/04-algorithms.md*

3. **CLI Implementation**
   - Implement all CLI commands per contracts
   - Add input validation and error handling for YAML team configs
   - Implement output formatting (JSON for results, text for summaries)
   - Add --help, --version, --format flags per constitutional requirements

4. **Statistics Implementation**
   - Implement simulation result aggregation
   - Add sensitivity analysis functionality
   - Implement comparison and reporting features

### Verification: Phase 1 Complete *(execution checkpoint)*
- [ ] All contract tests passing
- [ ] State machine validates against volleyball rules
- [ ] Team probability validation working
- [ ] All CLI commands functional

### Phase 2: Refinement

**Prerequisites** *(for execution)*: Phase 1 complete, all contract/integration tests passing
**Deliverables** *(from execution)*: Production-ready code with full test coverage

1. **Unit Tests** (for complex algorithms only)
   - State machine transition logic
   - Conditional probability calculations
   - Sensitivity analysis algorithms

2. **Performance Optimization** (only if metrics show need)
   - Optimize simulation loop for 10,000+ point simulations
   - Add progress reporting for long-running simulations

3. **Documentation Updates**
   - Update CLI help text and examples
   - Document team configuration YAML schema
   - Add usage examples for common scenarios

4. **Manual Testing Execution**
   - Follow manual-testing.md procedures
   - Verify all user stories work E2E
   - Document any issues found

### Verification: Phase 2 Complete *(execution checkpoint)*
- [ ] All tests passing (contract, integration, unit)
- [ ] Manual testing completed successfully
- [ ] Performance metrics meet requirements (10,000 points in 60 seconds)
- [ ] Documentation updated

---

## Success Criteria *(mandatory)*

1. **Constitutional**: All gates passed, no unjustified complexity
2. **Functional**: All feature requirements met per specification
3. **Testing**: Contract/Integration tests comprehensive, 80% coverage minimum
4. **Performance**: 10,000 point simulation completes within 60 seconds
5. **Simplicity**: Pure Python with PyYAML for readable configs, no unnecessary abstractions

---

## Review & Acceptance Checklist

### Plan Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] All mandatory sections completed
- [x] Technology stack fully specified (Python 3.8+, PyYAML for config files)
- [x] Dependencies justified (PyYAML for human-readable team configurations)

## Dependency Justification

### PyYAML Addition
**Package**: PyYAML  
**Purpose**: Human-readable team configuration files  
**Justification**: Team probability configurations are complex nested structures that coaches need to manually edit and understand. YAML provides:
- Human-readable format with comments
- Easier manual editing than JSON
- Better error messages for syntax issues
- Natural representation of nested probability matrices
- Industry standard for configuration files

**Alternatives Considered**: 
- JSON: Less readable, no comments, harder to manually edit
- TOML: Less suitable for deeply nested structures
- Plain text: Would require custom parsing

The user experience benefit of YAML for team configurations outweighs the minimal dependency cost.

---

### Constitutional Alignment
- [x] All Phase -1 gates passed
- [x] No deviations requiring Complexity Tracking section

### Technical Readiness
- [x] Phase 0 verification defined
- [x] Phase 1 implementation path clear
- [x] Success criteria measurable

### Risk Management
- [x] Complex areas identified (state machine, conditional probabilities)
- [x] Integration points clearly defined (library boundaries, CLI contracts)
- [x] Performance requirements specified (60 seconds for 10,000 points)
- [x] Security considerations addressed (input validation, no external dependencies)

### Implementation Clarity
- [x] All phases have clear prerequisites and deliverables
- [x] No speculative or "might need" features
- [x] Manual testing procedures defined

---

*This plan follows Constitution v2.0.0 (see `/memory/constitution.md`) emphasizing simplicity, framework trust, and integration-first testing.*