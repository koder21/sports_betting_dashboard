# Development Todo List

## Completed ✅
- [x] Bet placement system (AAI singles & parlays)
- [x] Custom bet builder (singles & parlays)
- [x] Database storage alignment
- [x] Dark mode for bet placement modal
- [x] Server imports working

## In Progress 🔄
- [ ] Test all AAI bet placement endpoints

## Short Term (Priority: HIGH)
- [ ] Test all AAI bet placement endpoints
- [ ] Verify grading works for AAI bets
- [x] Add toast notifications for success/error
- [ ] Test custom bet builder with multiple games

## Medium Term (Priority: MEDIUM)

### Props Integration (Future - When Ready)
**Note**: Manual odds entry actually ENABLES prop betting since users enter odds per-sportsbook
- [ ] Research prop betting data sources (The Odds API, DraftKings API, etc.)
- [ ] Add prop selection to bet builder UI
- [ ] Create prop scraper/integration service
- [ ] Test props with existing bet placement system
- [ ] Ensure prop bets store identically to game bets
- [ ] Add prop filtering/search to AAI page

### Analytics & Tracking
- [x] Create win rate analytics by source (AAI, Custom, Manual)

### UI Improvements
- [x] Add bet slip/parlay builder on separate page
- [x] Add bet tracking dashboard
- [x] Create mobile-friendly responsive layout
- [ ] Create AI betting configuration page (bankroll, daily bet amount, parlay preferences, risk tolerance, etc.)

## Long Term (Priority: LOW)

### Advanced Features
- [ ] Implement bankroll management
- [x] Add Kelly Criterion calculations
- [ ] Implement automatic lineup optimizer
- [ ] Add push notifications for line movements
- [x] Create betting strategy templates
- [ ] Add A/B testing framework for picks

### Integration
- [ ] Connect to real sportsbooks (API integration)
- [x] Auto-sync results when available
- [ ] Real-time odds syncing
- [x] Live game updates

### Performance & Scaling
- [ ] Database query optimization
- [ ] Add caching layer for frequent queries
- [ ] Implement bet archiving strategy
- [ ] Add search/filtering enhancements

---

## Notes
- Props can be integrated when needed - manual odds entry makes it feasible
- Current system works great for game spreads/moneylines/totals
- All features leverage same Bet model and grading system
