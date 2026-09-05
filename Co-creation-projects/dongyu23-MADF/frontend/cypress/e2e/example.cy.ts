describe('My First Test', () => {
  it('visits the app root', () => {
    cy.visit('/')
    cy.contains('MADF Web')
  })
})
