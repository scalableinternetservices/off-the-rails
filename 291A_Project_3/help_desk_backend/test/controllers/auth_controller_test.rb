require "test_helper"

class AuthControllerTest < ActionDispatch::IntegrationTest
  test "should get register" do
    get auth_register_url
    assert_response :success
  end

  test "should get login" do
    get auth_login_url
    assert_response :success
  end

  test "should get logout" do
    get auth_logout_url
    assert_response :success
  end

  test "should get refresh" do
    get auth_refresh_url
    assert_response :success
  end

  test "should get me" do
    get auth_me_url
    assert_response :success
  end
end
