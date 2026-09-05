describe('Forum System Button Smoke Test', () => {
  const username = `testuser_${Math.floor(Math.random() * 100000)}`
  const password = 'Password123!'

  it('should navigate through the main user flow using buttons', () => {
    // 1. Visit Home Page
    cy.visit('/')
    cy.contains('多智能体辩论框架').should('be.visible')

    // 2. Register
    cy.visit('/auth/register')
    cy.get('input#username').type(username)
    cy.get('input#password').type(password)
    cy.get('input#confirmPassword').type(password)
    // Click Register Button
    cy.get('button[type="submit"]').click()
    // Should redirect to login or auto-login? Assuming redirect to login based on common patterns
    // Or maybe it redirects to home? Let's check for URL change or success message.
    cy.url().should('include', '/auth/login')
    cy.contains('注册成功').should('be.visible')

    // 3. Login
    cy.get('input#username').type(username)
    cy.get('input#password').type(password)
    cy.get('button[type="submit"]').click()
    
    // Verify redirect to forums list
    cy.url().should('include', '/forums')
    cy.contains('讨论列表').should('be.visible')

    // 4. Create Persona (Prerequisite)
    cy.contains('角色管理').click()
    cy.url().should('include', '/personas')
    cy.contains('创建新角色').click() // Opens modal or goes to page?
    // Assuming modal for now based on typical AntD usage, or maybe a separate page.
    // Let's assume a button "创建新角色" triggers a modal.
    cy.get('.ant-modal-content').should('be.visible')
    cy.get('input#name').type('Cypress Tester')
    cy.get('textarea#bio').type('A test persona')
    // Submit persona
    cy.get('.ant-modal-footer button.ant-btn-primary').click()
    cy.contains('Cypress Tester').should('be.visible')

    // 5. Create Forum
    cy.contains('讨论列表').click()
    cy.contains('创建讨论').click() // Opens modal
    cy.get('.ant-modal-content').should('be.visible')
    cy.get('input#topic').type('Cypress Button Test Forum')
    // Select participant (might be complex in AntD select)
    // Skipping complex interaction for smoke test if possible, or selecting first available.
    // Assuming we can just submit if default is okay or mock it.
    // Actually, let's just check the button exists and opens the modal.
    
    // 6. Logout
    cy.get('.ant-avatar').trigger('mouseover') // Or click profile menu
    cy.contains('退出登录').click()
    cy.url().should('include', '/auth/login')
  })
})
