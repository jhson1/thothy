"use client";

import React, { useState, useEffect } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Container,
  useTheme,
  useMediaQuery,
  Avatar,
  Menu,
  MenuItem,
  IconButton,
  Divider,
  CircularProgress,
} from "@mui/material";
import { useAuth } from "../contexts/AuthContext";
import { useRouter } from "next/navigation";
import AccountCircle from "@mui/icons-material/AccountCircle";
import Logout from "@mui/icons-material/Logout";
import Link from "next/link";

interface HeaderProps {
  currentView:
    | "inbox"
    | "agent"
    | "find"
    | "staff"
    | "team"
    | "blog"
    | "login"
    | "agents"
    | "task";
}

interface PricingPolicyData {
  pricing_policy: string;
}

export default function Header({ currentView }: HeaderProps) {
  const { user, signIn, signOut, loading, supabase } = useAuth();
  const router = useRouter();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [pricingPolicy, setPricingPolicy] = useState<string | null>(null);
  const [policyLoading, setPolicyLoading] = useState(true);

  // Get user's display name and avatar
  const displayName = user?.user_metadata?.full_name || user?.email;
  const avatarUrl = user?.user_metadata?.avatar_url;

  // Fetch user's pricing policy
  useEffect(() => {
    const fetchPricingPolicy = async () => {
      if (!user) {
        setPolicyLoading(false);
        setPricingPolicy("Free");
        return;
      }

      try {
        // Get the user's pricing policy directly
        const { data: policyData, error: policyError } = await supabase
          .from("user_pricing_policy")
          .select("pricing_policy")
          .eq("user_id", user.id)
          .maybeSingle();

        // If there's no data or there's an error, default to Free
        if (policyError || !policyData) {
          setPricingPolicy("Free");
          setPolicyLoading(false);
          return;
        }

        // Set the policy from the data
        setPricingPolicy(policyData.pricing_policy || "Free");
        setPolicyLoading(false);
      } catch (error) {
        setPricingPolicy("Free");
        setPolicyLoading(false);
      }
    };

    fetchPricingPolicy();
  }, [user, supabase]);

  // Helper function for case-insensitive comparison
  const isPolicyType = (policyType: string): boolean => {
    return pricingPolicy?.toLowerCase() === policyType.toLowerCase();
  };

  // Function to check if a menu should be visible based on pricing policy
  const isMenuVisible = (menuType: "task") => {
    if (policyLoading || !pricingPolicy) return false;

    if (isPolicyType("Enterprise")) {
      return true;
    } else if (isPolicyType("Business")) {
      return menuType !== "task";
    } else {
      return !["task"].includes(menuType);
    }
  };

  const navButtonStyle = {
    textTransform: "none",
    fontSize: "1rem",
    minWidth: "auto",
    px: 2,
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleSignOut = () => {
    handleMenuClose();
    signOut();
  };

  // Get current path for redirect after login
  const handleSignIn = () => {
    signIn();
  };

  // Handle direct navigation
  const handleTothyClick = () => {
    router.push("/");
  };

  const handleAgentClick = () => {
    router.push("/agent");
  };

  const handleStaffClick = () => {
    router.push("/staff");
  };

  const handleBlogClick = () => {
    router.push("/blog");
  };

  const handleInboxClick = () => {
    router.push("/inbox");
  };

  const handleTeamClick = () => {
    router.push("/team");
  };

  // New handler for Task menu
  const handleTaskClick = () => {
    router.push("/task");
  };

  return (
    <AppBar
      position="static"
      color="transparent"
      elevation={0}
      sx={{ borderBottom: "2px solid rgba(0, 0, 0, 0.12)" }}
    >
      <Container maxWidth="lg">
        <Toolbar sx={{ justifyContent: "space-between", px: { xs: 0, sm: 2 } }}>
          <Typography
            variant="h5"
            component="div"
            onClick={handleTothyClick}
            sx={{
              fontFamily: "'Roboto Mono', monospace",
              fontWeight: 700,
              cursor: "pointer",
              color: "inherit",
            }}
          >
            Thothy
          </Typography>

          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            {currentView !== "login" && (
              <>
                {user && false && (
                  <Button
                    color={currentView === "inbox" ? "primary" : "inherit"}
                    onClick={handleInboxClick}
                    sx={{
                      ...navButtonStyle,
                      fontWeight: currentView === "inbox" ? 700 : 400,
                    }}
                  >
                    Inbox
                  </Button>
                )}

                <Button
                  color={
                    currentView === "agent" || currentView === "find"
                      ? "primary"
                      : "inherit"
                  }
                  onClick={handleAgentClick}
                  sx={{
                    ...navButtonStyle,
                    fontWeight:
                      currentView === "agent" || currentView === "find"
                        ? 700
                        : 400,
                  }}
                >
                  Agent
                </Button>

                {user && isMenuVisible("task") && (
                  <Button
                    color={currentView === "task" ? "primary" : "inherit"}
                    onClick={handleTaskClick}
                    sx={{
                      ...navButtonStyle,
                      fontWeight: currentView === "task" ? 700 : 400,
                    }}
                  >
                    Task
                  </Button>
                )}

                <Button
                  color={currentView === "blog" ? "primary" : "inherit"}
                  onClick={handleBlogClick}
                  sx={{
                    ...navButtonStyle,
                    fontWeight: currentView === "blog" ? 700 : 400,
                  }}
                >
                  Blog
                </Button>
              </>
            )}

            {user ? (
              <>
                <IconButton
                  size="large"
                  edge="end"
                  aria-label="account of current user"
                  aria-controls="menu-appbar"
                  aria-haspopup="true"
                  onClick={handleProfileMenuOpen}
                  color="inherit"
                >
                  <Avatar
                    src={avatarUrl}
                    alt={displayName}
                    sx={{
                      width: 32,
                      height: 32,
                      bgcolor: theme.palette.primary.main,
                    }}
                  >
                    {!avatarUrl && displayName?.charAt(0).toUpperCase()}
                  </Avatar>
                </IconButton>
                <Menu
                  anchorEl={anchorEl}
                  anchorOrigin={{
                    vertical: "bottom",
                    horizontal: "right",
                  }}
                  keepMounted
                  transformOrigin={{
                    vertical: "top",
                    horizontal: "right",
                  }}
                  open={Boolean(anchorEl)}
                  onClose={handleMenuClose}
                >
                  <MenuItem disabled>
                    <Box sx={{ display: "flex", flexDirection: "column" }}>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {displayName}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {user.email}
                      </Typography>
                    </Box>
                  </MenuItem>
                  <Divider />
                  <MenuItem onClick={handleSignOut}>
                    <Logout sx={{ mr: 1 }} />
                    Sign Out
                  </MenuItem>
                </Menu>
              </>
            ) : loading ? (
              <Box sx={{ display: "flex", alignItems: "center", ml: 2 }}>
                <CircularProgress size={24} color="primary" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Checking login...
                </Typography>
              </Box>
            ) : (
              <Button
                variant="contained"
                color="primary"
                onClick={handleSignIn}
                sx={{ ml: 2 }}
              >
                Sign in with Google
              </Button>
            )}
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
