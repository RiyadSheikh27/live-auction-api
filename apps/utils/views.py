from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status

class APIResponse:
    @staticmethod
    def success_response(data=None, message="Request Successfull", status_code=status.HTTP_200_OK):
        return Response(
            {
                "success": True,
                "message": message,
                "data": data,
                "errors": None
            }, status=status_code
        )
    @staticmethod
    def error_response(errors=None, message="Something went wrong", status_code=status.HTTP_400_BAD_REQUEST):
        """
        Returns a standard error response.
        """
        return Response({
            "success": False,
            "message": message,
            "data": None,
            "errors": errors
        }, status=status_code)