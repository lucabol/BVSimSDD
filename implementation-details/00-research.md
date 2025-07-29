# Beach Volleyball Rules Research

## Research Summary

This document captures the key findings from researching beach volleyball rules and point progression to ensure accurate state machine modeling.

## Key Findings

### Point Progression Flow

1. **Serve Phase**
   - Only serving team can initiate serve
   - Outcomes: Ace (immediate point), Service Error (immediate point loss), In Play (continues)

2. **Receive Phase** 
   - Only receiving team handles serve reception
   - Quality levels: Excellent, Good, Poor, Error (immediate point loss)

3. **Set Phase**
   - Team that received serve performs set (their 2nd touch)
   - Quality affects attack probability: Excellent > Good > Poor

4. **Attack Phase**
   - Same team as receive/set performs attack (their 3rd touch)
   - Outcomes: Kill (point won), Error (point lost), Defended (continues to other team)

5. **Defense Phase**
   - Original serving team defends
   - Block outcomes: Stuff (point won), Deflection (continues), No Touch (ball goes to dig)
   - Dig outcomes: Excellent/Good/Poor/Error quality affects counterattack

6. **Transition**
   - After successful defense, teams switch offensive/defensive roles
   - Rally continues until point conclusion

### Critical Rules for State Machine

- **Team Alternation**: Teams must alternate touches after ball crosses net
- **Three-Touch Rule**: Each team has maximum 3 touches before returning ball
- **Block Counting**: Block counts as one of the three touches
- **Role Switching**: Serving/receiving roles switch after each point conclusion

### Conditional Probability Relationships

Research confirmed that volleyball skills are highly contextual:
- Attack success strongly depends on set quality
- Defense effectiveness varies by attack type and power
- Dig quality affects subsequent counterattack options
- Serve placement affects reception difficulty

## State Machine Validation

The research validates our state machine design with:
- Distinct serving/receiving team states
- Conditional probability matrices based on previous action quality
- Proper team role alternation
- Accurate point conclusion conditions

## Source Validation

Rules verified against:
- Official FIVB beach volleyball regulations
- Olympic competition standards
- Statistical analysis of professional match data